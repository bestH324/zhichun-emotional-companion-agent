"""会话管理细粒度测试：隔离、uuid4、TTL、显式结束、后台清理、统计。"""
import time

from app.modules.session import SessionManager


def test_create_generates_uuid4():
    m = SessionManager()
    s = m.get_or_create("")
    assert len(s.session_id) == 32
    assert s.turn_count == 0


def test_reuse_existing_session():
    m = SessionManager()
    sid = m.get_or_create("").session_id
    s2 = m.get_or_create(sid)
    assert s2.session_id == sid


def test_unknown_id_generates_new_session():
    m = SessionManager()
    s = m.get_or_create("unknown-abc")
    assert s.session_id != "unknown-abc"
    assert len(s.session_id) == 32


def test_isolation_between_sessions():
    m = SessionManager()
    a = m.get_or_create("")
    b = m.get_or_create("")
    assert a is not b
    a.turn_count = 5
    assert b.turn_count == 0


def test_end_returns_true_only_for_existing():
    m = SessionManager()
    sid = m.get_or_create("").session_id
    assert m.end(sid) is True
    assert m.end(sid) is False  # 幂等：第二次结束返回 False
    assert m.get(sid) is None


def test_ttl_expiry_get_returns_none():
    m = SessionManager(ttl_seconds=1)
    sid = m.get_or_create("").session_id
    time.sleep(1.1)
    assert m.get(sid) is None
    assert m.count() == 0


def test_ttl_get_or_create_recreates():
    m = SessionManager(ttl_seconds=1)
    sid = m.get_or_create("").session_id
    time.sleep(1.1)
    s2 = m.get_or_create(sid)  # 旧 id 已过期，忽略传入，生成新会话
    assert s2.session_id != sid


def test_touch_keeps_session_alive():
    m = SessionManager(ttl_seconds=1)
    sid = m.get_or_create("").session_id
    time.sleep(0.6)
    m.touch(sid)  # 刷新活跃时间
    time.sleep(0.6)
    assert m.get(sid) is not None  # 未过期


def test_cleanup_removes_all_expired():
    m = SessionManager(ttl_seconds=1)
    for _ in range(3):
        m.get_or_create("")
    assert m.count() == 3
    time.sleep(1.1)
    removed = m.cleanup()
    assert removed == 3
    assert m.count() == 0


def test_cleanup_keeps_fresh():
    m = SessionManager(ttl_seconds=1)
    m.get_or_create("")
    time.sleep(1.1)
    fresh = m.get_or_create("").session_id  # 新建一个未过期的
    removed = m.cleanup()
    assert removed == 1  # 只清掉第一个过期的
    assert m.get(fresh) is not None


def test_background_cleanup_runs_without_access():
    m = SessionManager(ttl_seconds=1)
    m.start_cleanup(interval_seconds=0.2)
    try:
        m.get_or_create("")
        assert m.count() == 1
        # 不访问，等待后台线程自动清理
        deadline = time.time() + 3
        while m.count() > 0 and time.time() < deadline:
            time.sleep(0.1)
        assert m.count() == 0
    finally:
        m.stop_cleanup()


def test_start_cleanup_is_idempotent():
    m = SessionManager(ttl_seconds=999)
    m.start_cleanup(interval_seconds=0.1)
    first_thread = m._cleanup_thread
    m.start_cleanup(interval_seconds=0.1)  # 不应重复启动
    assert m._cleanup_thread is first_thread
    m.stop_cleanup()
    assert m._cleanup_thread is None


def test_stop_cleanup_noop_without_start():
    m = SessionManager(ttl_seconds=999)
    m.stop_cleanup()  # 不应抛异常
