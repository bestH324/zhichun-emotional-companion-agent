"""MockLLM 三原则测试：对齐规划书 §7 测试方案第 5 项。"""
from app.config import MBTI_TYPES
from app.llm.mock import MockLLM
from app.prompts.mbti_prompts import get_mbti_prompt
from app.schemas import EmotionResult, Message


def test_deterministic_same_input_same_output():
    llm = MockLLM()
    args = (get_mbti_prompt("INTJ"), "用户说：你好", [])
    assert llm.generate(*args) == llm.generate(*args)


def test_generate_contains_style_marker():
    llm = MockLLM()
    reply = llm.generate(get_mbti_prompt("ENFP"), "用户说：你好", [])
    # 回复必须含可预测标记：共情句前缀 + 风格特征词
    assert "我理解你现在的感受" in reply
    assert "热情奔放" in reply  # ENFP 的风格特征词


def test_different_mbti_distinct_style():
    llm = MockLLM()
    r1 = llm.generate(get_mbti_prompt("ENFP"), "用户说：你好", [])
    r2 = llm.generate(get_mbti_prompt("INTJ"), "用户说：你好", [])
    assert r1 != r2  # 不同 MBTI 风格措辞可区分
    assert "热情奔放" in r1
    assert "理性前瞻" in r2


def test_generate_mentions_facts_when_present():
    llm = MockLLM()
    reply = llm.generate(
        get_mbti_prompt("general"),
        "用户说：你好\n[用户画像] 姓名：小明",
        [],
    )
    assert "记得" in reply  # 事实引用标记


def test_infer_mbti_is_deterministic_and_valid():
    llm = MockLLM()
    history = [Message(role="user", content="我喜欢猫")]
    assert llm.infer_mbti(history) in MBTI_TYPES
    assert llm.infer_mbti(history) == llm.infer_mbti(history)  # 确定性


def test_classify_emotion_fallback_default():
    llm = MockLLM()
    r = llm.classify_emotion("任意文本")
    assert isinstance(r, EmotionResult)
    assert r.emotion == "平静"
    assert r.intensity == 0.5
