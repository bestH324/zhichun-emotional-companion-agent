"""Mock 数字人渲染：情绪标签 → 表情标识。"""
from app.schemas import Expression

EMOTION_TO_EXPRESSION = {
    "开心": ("微笑", "open"),
    "平静": ("平静", "closed"),
    "焦虑": ("皱眉", "slightly_open"),
    "悲伤": ("落泪", "open"),
    "压力大": ("疲惫", "slightly_open"),
    "愤怒": ("怒视", "open"),
    "孤独": ("低头", "closed"),
}

_DEFAULT = ("平静", "closed")


def render_expression(emotion: str) -> Expression:
    expression, mouth_state = EMOTION_TO_EXPRESSION.get(emotion, _DEFAULT)
    return Expression(emotion=emotion, expression=expression, mouth_state=mouth_state)
