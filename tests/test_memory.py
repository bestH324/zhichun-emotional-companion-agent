"""三层记忆细粒度测试：对齐规划书 §7 测试方案第 3 项。"""
from app.agents.memory_agent import MemoryAgent
from app.config import EPISODIC_TOP_K, SHORT_TERM_N
from app.modules.memory_store import MemoryStore
from app.modules.session import Session
from app.schemas import Message


def _session() -> Session:
    return Session(session_id="s")


def _msg(role: str, content: str) -> Message:
    return Message(role=role, content=content)


# ===== 短期记忆 =====
def test_short_term_keeps_recent_n_rounds():
    store = MemoryStore()
    s = _session()
    # 写入 N+1 轮（每轮 user+assistant 两条）
    for i in range(SHORT_TERM_N + 1):
        store.add_message(s, _msg("user", f"u{i}"))
        store.add_message(s, _msg("assistant", f"a{i}"))
    short = store.get_short_term(s)
    # 只保留最近 N 轮 = 2N 条
    assert len(short) == SHORT_TERM_N * 2
    # 最早的第 0 轮被截掉，剩下第 1..N 轮
    assert short[0].content == "u1"
    assert short[-1].content == f"a{SHORT_TERM_N}"


def test_short_term_not_truncated_within_n():
    store = MemoryStore()
    s = _session()
    for i in range(SHORT_TERM_N - 1):
        store.add_message(s, _msg("user", f"u{i}"))
        store.add_message(s, _msg("assistant", f"a{i}"))
    assert len(store.get_short_term(s)) == (SHORT_TERM_N - 1) * 2


# ===== 情景记忆 =====
def test_episodic_recall_by_keyword_overlap():
    store = MemoryStore()
    s = _session()
    store.add_message(s, _msg("user", "我喜欢猫"))
    store.add_message(s, _msg("assistant", "好的"))
    store.add_message(s, _msg("user", "我喜欢狗"))
    store.add_message(s, _msg("assistant", "明白"))
    # query 与「我喜欢猫」有交集
    result = store.recall_episodic(s, "你喜欢猫吗")
    assert result and "我喜欢猫" in result


def test_episodic_recall_top_k_limit():
    store = MemoryStore()
    s = _session()
    for i in range(EPISODIC_TOP_K + 2):
        store.add_message(s, _msg("user", "我喜欢猫咪"))
        store.add_message(s, _msg("assistant", "嗯"))
    result = store.recall_episodic(s, "猫咪")
    assert len(result) == EPISODIC_TOP_K  # 召回数不超过 top_k


def test_episodic_recall_empty_when_no_overlap():
    store = MemoryStore()
    s = _session()
    store.add_message(s, _msg("user", "我喜欢猫"))
    store.add_message(s, _msg("assistant", "好的"))
    # 无交集关键词 → 不召回
    assert store.recall_episodic(s, "今天天气怎么样") == []


def test_episodic_recall_empty_for_stopword_only_query():
    store = MemoryStore()
    s = _session()
    store.add_message(s, _msg("user", "我喜欢猫"))
    # 纯停用字/空 query → 无关键词 → 空
    assert store.recall_episodic(s, "") == []


def test_episodic_sorted_by_score_desc():
    store = MemoryStore()
    s = _session()
    store.add_message(s, _msg("user", "喜欢狗"))      # 交集少 → 得分低
    store.add_message(s, _msg("assistant", "好的"))
    store.add_message(s, _msg("user", "我喜欢猫"))     # 交集多 → 得分高
    store.add_message(s, _msg("assistant", "嗯"))
    result = store.recall_episodic(s, "我喜欢猫")
    # 得分高的「我喜欢猫」应排在前，得分低的「喜欢狗」在后
    assert result[0] == "我喜欢猫"
    assert "喜欢狗" in result


def test_episodic_recall_single_char_keyword():
    store = MemoryStore()
    s = _session()
    store.add_message(s, _msg("user", "我喜欢猫"))
    store.add_message(s, _msg("assistant", "好的"))
    # 单字实义词也能召回
    assert store.recall_episodic(s, "猫") == ["我喜欢猫"]


# ===== 事实记忆 =====
def test_fact_extract_basic_patterns():
    store = MemoryStore()
    s = _session()
    store.extract_facts(s, "我叫小明")
    store.extract_facts(s, "我喜欢唱歌")
    store.extract_facts(s, "我住在北京")
    store.extract_facts(s, "我讨厌香菜")
    assert s.facts == {
        "姓名": "小明",
        "偏好": "唱歌",
        "居住地": "北京",
        "厌恶": "香菜",
    }


def test_fact_same_key_overwrite():
    store = MemoryStore()
    s = _session()
    store.extract_facts(s, "我喜欢唱歌")
    store.extract_facts(s, "我喜欢跳舞")  # 同名 key 新值覆盖
    assert s.facts["偏好"] == "跳舞"
    assert len(s.facts) == 1


def test_fact_no_hit_adds_nothing():
    store = MemoryStore()
    s = _session()
    store.extract_facts(s, "今天天气不错")
    assert s.facts == {}


def test_fact_trailing_no_punctuation():
    store = MemoryStore()
    s = _session()
    store.extract_facts(s, "我叫小明")  # 句尾无标点
    assert s.facts["姓名"] == "小明"


# ===== 隔离 + 组装 =====
def test_memory_isolation_between_sessions():
    store = MemoryStore()
    a = _session()
    b = _session()
    store.add_message(a, _msg("user", "我喜欢猫"))
    store.extract_facts(a, "我叫小明")
    # b 会话完全独立
    assert store.get_short_term(b) == []
    assert store.get_facts(b) == {}
    assert store.recall_episodic(b, "猫") == []


def test_assemble_context_merges_three_layers():
    store = MemoryStore()
    agent = MemoryAgent(store)
    s = _session()
    store.add_message(s, _msg("user", "我喜欢猫"))
    store.add_message(s, _msg("assistant", "好的"))
    store.extract_facts(s, "我叫小明")

    ctx = agent.assemble_context(s, "猫")
    assert "short_term" in ctx and "episodic" in ctx and "facts" in ctx
    assert ctx["facts"] == {"姓名": "小明"}
    assert ctx["short_term"]  # 非空
    # 情景召回含「我喜欢猫」
    assert any("我喜欢猫" in t for t in ctx["episodic"])
