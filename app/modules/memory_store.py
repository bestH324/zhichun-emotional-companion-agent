"""三层记忆存储：短期 / 情景 / 事实，全部按 session 隔离。"""
import re

from app.config import EPISODIC_TOP_K, SHORT_TERM_N
from app.modules.session import Session
from app.schemas import Message

# 事实提取句式 → 字段名
FACT_PATTERNS = [
    (r"我喜欢(.+?)(?:[，。！？\s]|$)", "偏好"),
    (r"我讨厌(.+?)(?:[，。！？\s]|$)", "厌恶"),
    (r"我叫(.+?)(?:[，。！？\s]|$)", "姓名"),
    (r"我住在(.+?)(?:[，。！？\s]|$)", "居住地"),
]

# 停用字（用于关键词 bigram 过滤）
_STOP = set("的了我你他她它是在和也就都吗呢吧啊哦很挺不没有这那")


class MemoryStore:
    def add_message(self, session: Session, msg: Message) -> None:
        session.short_term.append(msg)
        # 短期记忆只保留最近 N 轮（每轮 user+assistant 两条）
        while len(session.short_term) > SHORT_TERM_N * 2:
            session.short_term.popleft()
        # 全历史文本（情景召回数据源）
        session.episodic.append(msg.content)
        # 本切片累积消息（供 MBTI 推断，切片完成时由 router 清空）
        session.slice_buffer.append(msg)

    def get_short_term(self, session: Session) -> list[Message]:
        return list(session.short_term)

    def recall_episodic(self, session: Session, query: str) -> list[str]:
        """按关键词交集打分，返回 score > 0 的 top-k 条历史文本。"""
        q_kws = _keywords(query)
        if not q_kws:
            return []
        scored = []
        for text in session.episodic:
            score = len(q_kws & _keywords(text))
            if score > 0:
                scored.append((score, text))
        scored.sort(key=lambda x: -x[0])
        return [text for _, text in scored[:EPISODIC_TOP_K]]

    def extract_facts(self, session: Session, text: str) -> None:
        """规则提取新事实，同名 key 新值覆盖。"""
        for pattern, field in FACT_PATTERNS:
            m = re.search(pattern, text)
            if m:
                value = m.group(1).strip()
                if value:
                    session.facts[field] = value

    def get_facts(self, session: Session) -> dict[str, str]:
        return dict(session.facts)


def _keywords(text: str) -> set[str]:
    """中文零依赖分词近似：去停用字后，取「非停用单字 + 相邻 bigram」作为关键词。

    单字覆盖「猫/狗/茶」等单字实义词，bigram 覆盖「喜欢/天气」等双字词，
    二者并集作为关键词集合，保证确定性、可断言。
    """
    segments = re.findall(r"[一-龥A-Za-z]+", text)
    kws: set[str] = set()
    for seg in segments:
        chars = [c for c in seg if c not in _STOP]  # 去停用字
        kws.update(chars)                            # 非停用单字
        for i in range(len(chars) - 1):
            kws.add(chars[i] + chars[i + 1])         # 相邻 bigram
    return kws
