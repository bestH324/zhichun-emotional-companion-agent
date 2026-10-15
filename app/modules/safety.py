"""安全风控：风险词命中短路，返回固定安全回复。"""
from app.schemas import SafetyResult

# 风险关键词：自伤/自杀、极端负面、心理诊断与诊疗请求
# 注意：诊疗请求类收窄为「明确求助式」短语，避免误伤「医生诊断是感冒」等正常陈述
RISK_KEYWORDS = [
    "自杀", "自残", "不想活", "去死", "割腕", "跳楼", "了结自己",
    "帮我诊断", "给我诊断", "诊断一下", "开点药", "给我开药", "开个药方",
    "是不是抑郁", "抑郁症", "焦虑症", "心理诊断", "心理疾病", "处方药",
]

SAFETY_REPLY = (
    "本产品仅为 AI 陪伴助手，无法替代专业心理咨询。"
    "如有严重情绪困扰，请寻求学校心理中心等专业帮助。"
)


def check_safety(text: str) -> SafetyResult:
    for kw in RISK_KEYWORDS:
        if kw in text:
            return SafetyResult(hit=True, reply=SAFETY_REPLY)
    return SafetyResult(hit=False)
