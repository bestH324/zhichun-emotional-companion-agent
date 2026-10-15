"""情感识别：规则词典为主，未命中调 LLM 兜底。"""
from app.llm.base import LLMClient
from app.schemas import EmotionResult

# 每类情绪的关键词词典，值为强度权重（0~1）
KEYWORDS: dict[str, dict[str, float]] = {
    "开心": {"开心": 0.9, "高兴": 0.8, "太好了": 0.9, "喜欢": 0.6, "开心死了": 1.0, "快乐": 0.8},
    "悲伤": {"难过": 0.9, "伤心": 0.9, "想哭": 1.0, "哭了": 0.9, "悲伤": 0.9, "失落": 0.7},
    "焦虑": {"焦虑": 0.9, "担心": 0.8, "紧张": 0.8, "不安": 0.8, "害怕": 0.7, "忐忑": 0.8},
    "压力大": {"压力大": 1.0, "压力": 0.7, "累死了": 0.9, "喘不过气": 0.9, "忙": 0.5, "崩溃": 0.8},
    "愤怒": {"生气": 0.9, "愤怒": 0.9, "气死": 1.0, "讨厌": 0.7, "火大": 0.9, "烦死了": 0.8},
    "孤独": {"孤独": 0.9, "寂寞": 0.9, "没人陪": 0.9, "一个人": 0.7, "孤单": 0.9},
    "平静": {"平静": 0.7, "还好": 0.5, "还行": 0.5, "没事": 0.5},
}


def _match(text: str) -> tuple[str, float] | None:
    best_emotion, best_score = None, 0.0
    for emotion, words in KEYWORDS.items():
        for word, weight in words.items():
            if word in text and weight > best_score:
                best_emotion, best_score = emotion, weight
    return (best_emotion, best_score) if best_emotion else None


def recognize_emotion(text: str, llm: LLMClient) -> EmotionResult:
    """规则命中返回最高强度情绪；未命中走 LLM 兜底（Mock 固定返回「平静」）。"""
    hit = _match(text)
    if hit:
        return EmotionResult(emotion=hit[0], intensity=hit[1])
    return llm.classify_emotion(text)
