"""并发与隔离验证：单会话顺序处理不丢计数，多会话互不串扰。"""
import threading

from app.agents.router_agent import process_chat
from app.modules.session import SessionManager


def _new_manager() -> SessionManager:
    return SessionManager(ttl_seconds=99999)


def test_single_session_concurrent_no_lost_turn():
    """同一 session 并发 N 次，计数必须恰好 N（不丢失、不重复）。"""
    m = _new_manager()
    # 先创建会话，拿到 uuid4
    sid = process_chat("", "初始化", manager=m).session_id

    n_threads = 20
    errors: list[Exception] = []

    def worker(i):
        try:
            process_chat(sid, f"并发消息{i}", manager=m)
        except Exception as e:  # noqa: BLE001
            errors.append(e)

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(n_threads)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert errors == []
    sess = m.get(sid)
    # 1 次初始化 + 20 次并发，共 21 轮，计数必须精确
    assert sess.turn_count == 1 + n_threads
    # 短期记忆条数 = 21 轮 × 2 条 = 42（未超 N=10 截断则更少，但此处只验证不越界/不丢）
    assert len(sess.short_term) <= 10 * 2


def test_multi_session_parallel_no_cross_talk():
    """不同 session 并发对话，各自计数与记忆隔离。"""
    m = _new_manager()
    ids = [process_chat("", f"会话{i}初始化", manager=m).session_id for i in range(5)]

    def worker(sid):
        for _ in range(10):
            process_chat(sid, "消息", manager=m)

    threads = [threading.Thread(target=worker, args=(sid,)) for sid in ids]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    for sid in ids:
        sess = m.get(sid)
        # 1 次初始化 + 10 次 = 11 轮
        assert sess.turn_count == 11, f"session {sid} 计数错乱: {sess.turn_count}"


def test_end_and_chat_serialize_no_deadlock():
    """end 与 process_chat 并发：不抛异常、不死锁、结束语义幂等。"""
    m = _new_manager()
    sid = process_chat("", "初始化", manager=m).session_id

    errors: list[Exception] = []
    ended_flags: list[bool] = []

    def chat_worker():
        try:
            for _ in range(30):
                process_chat(sid, "普通消息", manager=m)
        except Exception as e:  # noqa: BLE001
            errors.append(e)

    def end_worker():
        try:
            for _ in range(10):
                ended_flags.append(m.end(sid))
        except Exception as e:  # noqa: BLE001
            errors.append(e)

    t1 = threading.Thread(target=chat_worker)
    t2 = threading.Thread(target=end_worker)
    t1.start(); t2.start()
    t1.join(); t2.join()

    assert errors == []  # 无异常、无死锁
    # end 幂等：最多一次返回 True（首次真正移除），其余 False
    assert ended_flags.count(True) <= 1
