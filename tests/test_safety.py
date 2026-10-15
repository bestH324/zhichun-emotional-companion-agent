"""安全风控细粒度测试：对齐规划书 §7 测试方案第 4 项。"""
import pytest

from app.modules.safety import SAFETY_REPLY, check_safety


@pytest.mark.parametrize("text", [
    "我想自杀",
    "我最近在自残",
    "不想活了",
    "帮我诊断一下是不是抑郁",
    "我是不是抑郁了",
    "能给我开点药吗",
])
def test_risk_keywords_hit(text):
    result = check_safety(text)
    assert result.hit is True
    assert result.reply == SAFETY_REPLY
    assert "专业" in result.reply


@pytest.mark.parametrize("text", [
    "我今天心情不太好",
    "最近学习压力有点大",
    "你能陪我说说话吗",
    "我觉得很孤独",
])
def test_normal_text_not_hit(text):
    result = check_safety(text)
    assert result.hit is False
    assert result.reply is None


def test_no_false_positive_on_medical_statement():
    # 收窄后的关键词不应误伤正常医疗陈述（修复「诊断」过宽误伤）
    result = check_safety("医生诊断我是普通感冒，吃点药就好了")
    assert result.hit is False
