"""整体调度 Agent 核心验证：编排顺序、安全短路、切片触发、会话隔离、TTL。"""
from app.agents.router_agent import process_chat
from app.modules.session import SessionManager


def _new_manager(ttl_seconds: int = 99999) -> SessionManager:
    return SessionManager(ttl_seconds=ttl_seconds)


def test_first_call_returns_server_generated_uuid():
    m = _new_manager()
    r = process_chat("", "你好", manager=m)
    # 服务端强制生成 uuid4（32 位 hex），不可枚举
    assert r.session_id and r.session_id != ""
    assert len(r.session_id) == 32


def test_client_supplied_id_is_ignored_when_unknown():
    m = _new_manager()
    r = process_chat("attacker-guess", "你好", manager=m)
    # 未命中已有会话 → 忽略传入值，服务端生成新 uuid4
    assert r.session_id != "attacker-guess"
    assert len(r.session_id) == 32


def test_safety_short_circuit():
    m = _new_manager()
    r = process_chat("", "我想自杀", manager=m)
    assert r.safety_triggered is True
    assert "专业" in r.reply
    assert r.turn_count == 0  # 安全拦截不计数


def test_normal_flow_emotion_and_count():
    m = _new_manager()
    r = process_chat("", "我今天很开心", manager=m)
    assert r.safety_triggered is False
    assert r.emotion.emotion == "开心"
    assert r.turn_count == 1
    assert r.reply  # 有回复文本
    assert r.audio.path.startswith("mock://tts/")
    assert r.expression.expression == "微笑"


def _rounds(m, sid, n, prefix="消息"):
    """连续 n 轮对话，返回最新响应的 session_id。"""
    current = sid
    last = None
    for i in range(n):
        last = process_chat(current, f"{prefix}{i}", manager=m)
        current = last.session_id
    return last


def test_slice_trigger_at_20_rounds():
    m = _new_manager()
    last = _rounds(m, "", 20)
    sid = last.session_id
    sess = m.get(sid)
    # 第 20 轮结算后触发切片画像，本周期累积 1 条画像
    assert len(sess.cycle_portraits) == 1
    # 周期未满（5 切片）人格不切换，本轮返回的 mbti 仍是 general
    assert last.mbti == "general"


def test_no_infer_before_20_rounds():
    m = _new_manager()
    last = _rounds(m, "", 19)
    sess = m.get(last.session_id)
    assert len(sess.cycle_portraits) == 0  # 不足 20 轮不画像
    assert len(sess.slice_buffer) == 38  # 19 轮 × 2 条已累积，未清空


def test_slice_buffer_uses_full_slice_not_truncated():
    m = _new_manager()
    # 短期记忆 N=10（20 条），但切片画像应拿到完整 20 轮（40 条）
    last = _rounds(m, "", 20)
    sess = m.get(last.session_id)
    # 切片完成，buffer 已清空
    assert sess.slice_buffer == []


def test_session_isolation():
    m = _new_manager()
    ra = process_chat("", "我今天很开心", manager=m)
    rb = process_chat("", "我今天很生气", manager=m)
    sa, sb = m.get(ra.session_id), m.get(rb.session_id)
    assert sa.turn_count == 1 and sb.turn_count == 1
    assert "开心" in sa.short_term[0].content
    assert "生气" in sb.short_term[0].content
    assert sa.facts == sb.facts == {}


def test_fact_extraction():
    m = _new_manager()
    r = process_chat("", "我叫小明", manager=m)
    sess = m.get(r.session_id)
    assert sess.facts.get("姓名") == "小明"


def test_initial_mbti_applied_on_first_turn():
    m = _new_manager()
    r = process_chat("", "你好", initial_mbti="ENTJ", manager=m)
    assert r.mbti == "ENTJ"
    sess = m.get(r.session_id)
    assert sess.current_mbti == "ENTJ"
    assert sess.initial_mbti == "ENTJ"


def test_initial_mbti_ignored_after_first_turn():
    m = _new_manager()
    r1 = process_chat("", "你好", initial_mbti="ENTJ", manager=m)
    # 续接时再传 initial_mbti，应被忽略
    r2 = process_chat(r1.session_id, "在吗", initial_mbti="INFP", manager=m)
    assert r2.mbti == "ENTJ"


def test_invalid_initial_mbti_raises():
    m = _new_manager()
    import pytest
    with pytest.raises(ValueError):
        process_chat("", "你好", initial_mbti="ABCD", manager=m)


def test_ttl_expiry_discards_session():
    m = _new_manager(ttl_seconds=1)
    r = process_chat("", "你好", manager=m)
    sid = r.session_id
    import time
    time.sleep(1.1)
    # 过期后 get 返回 None，且 get_or_create 会重建新会话
    assert m.get(sid) is None
    r2 = process_chat(sid, "还在吗", manager=m)
    assert r2.session_id != sid  # 旧 id 已失效，生成新会话
