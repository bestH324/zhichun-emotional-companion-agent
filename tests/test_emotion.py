"""情感识别细粒度测试：对齐规划书 §7 测试方案第 1 项。"""
import pytest

from app.llm.mock import MockLLM
from app.modules.emotion import recognize_emotion
from app.schemas import EmotionResult


@pytest.fixture
def llm():
    return MockLLM()


# 每类关键词各断言正确标签与强度
@pytest.mark.parametrize("text,expected_emotion,expected_intensity", [
    ("我今天太开心了", "开心", 0.9),
    ("我很难过", "悲伤", 0.9),
    ("我有点担心", "焦虑", 0.8),
    ("最近压力大", "压力大", 1.0),
    ("我真的很生气", "愤怒", 0.9),
    ("我觉得好孤独", "孤独", 0.9),
    ("我还好", "平静", 0.5),
])
def test_rule_keyword_hits(text, expected_emotion, expected_intensity, llm):
    result = recognize_emotion(text, llm)
    assert result.emotion == expected_emotion
    assert result.intensity == pytest.approx(expected_intensity)


def test_multi_hit_returns_highest_intensity(llm):
    # 「开心死了」强度 1.0 > 「开心」0.9，应取强度最高者
    result = recognize_emotion("开心死了", llm)
    assert result.emotion == "开心"
    assert result.intensity == 1.0


def test_no_hit_falls_back_to_llm(llm):
    # 无任何关键词命中 → 走 LLM 兜底（Mock 固定「平静」0.5）
    result = recognize_emotion("今天的天气不错呢", llm)
    assert result.emotion == "平静"
    assert result.intensity == 0.5


def test_result_is_emotion_result_type(llm):
    result = recognize_emotion("我很开心", llm)
    assert isinstance(result, EmotionResult)
    assert 0.0 <= result.intensity <= 1.0
