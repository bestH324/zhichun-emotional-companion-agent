"""SQLite 持久化测试：会话元数据 + 消息 + 事实跨实例恢复（模拟重启）。"""
import tempfile

from app.modules.memory_store import MemoryStore
from app.modules.session import SessionManager


def _tmp_db():
    return tempfile.mktemp(suffix=".db")


def test_session_restore_across_instances():
    """写入会话 → 新建 SessionManager（模拟重启）→ 恢复出相同 turn_count / facts。"""
    db = _tmp_db()
    m1 = SessionManager(db_path=db)
    store1 = MemoryStore(db_path=db)
    sess = m1.get_or_create("")
    sid = sess.session_id
    # 模拟一轮对话：写消息 + 事实 + 轮次 + 落盘
    store1.add_message(sess, _msg("user", "我叫小明"))
    store1.extract_facts(sess, "我叫小明")
    sess.turn_count = 1
    m1.save(sess)

    # 模拟重启：新实例，同一 db 路径
    m2 = SessionManager(db_path=db)
    restored = m2.get_or_create(sid)
    assert restored.session_id == sid
    assert restored.turn_count == 1
    assert restored.facts.get("姓名") == "小明"


def test_messages_restored_into_short_term_and_episodic():
    db = _tmp_db()
    m1 = SessionManager(db_path=db)
    store1 = MemoryStore(db_path=db)
    sess = m1.get_or_create("")
    sid = sess.session_id
    store1.add_message(sess, _msg("user", "我喜欢猫"))
    store1.add_message(sess, _msg("assistant", "好的"))
    m1.save(sess)

    m2 = SessionManager(db_path=db)
    restored = m2.get_or_create(sid)
    # episodic 恢复全量历史文本
    assert "我喜欢猫" in restored.episodic
    # short_term 恢复消息
    assert any(m.content == "我喜欢猫" for m in restored.short_term)


def test_end_session_deletes_from_db():
    db = _tmp_db()
    m1 = SessionManager(db_path=db)
    r = m1.get_or_create("")
    sid = r.session_id
    m1.save(r)
    m1.end(sid)

    m2 = SessionManager(db_path=db)
    # 已删除，不应恢复，而应新建
    sess = m2.get_or_create(sid)
    assert sess.session_id != sid


def test_no_db_path_stays_in_memory():
    """无 db_path 时仍为纯内存，不落盘，行为与历史一致。"""
    m = SessionManager()
    sess = m.get_or_create("")
    assert sess.session_id
    assert m._storage is None


def _msg(role: str, content: str):
    from app.schemas import Message
    return Message(role=role, content=content)
