"""数据结构：所有跨模块传递的数据统一使用 Pydantic v2。"""
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from app.config import MAX_INPUT_LENGTH, VALID_MBTI


class Message(BaseModel):
    """统一消息格式：记忆、LLM history、切片摘要共用。"""
    role: Literal["user", "assistant"]
    content: str


class EmotionResult(BaseModel):
    emotion: str          # 取值见 config.EMOTIONS
    intensity: float      # 0.0 ~ 1.0


class AudioMeta(BaseModel):
    text: str             # 原文
    emotion: str
    duration_ms: int      # 由文本长度估算
    path: str             # mock 占位，如 "mock://tts/<uuid>.wav"


class Expression(BaseModel):
    emotion: str
    expression: str       # 表情标识，如 "微笑"
    mouth_state: str      # 口型状态，如 "open"


class ChatRequest(BaseModel):
    session_id: str = ""                 # 允许为空，空则由服务端生成 uuid4
    text: str = Field(min_length=1, max_length=MAX_INPUT_LENGTH)
    initial_mbti: str | None = None      # 可选初始人格（仅首次对话生效，续接时忽略）

    @field_validator("initial_mbti")
    @classmethod
    def _check_initial_mbti(cls, v):
        if v is not None and v not in VALID_MBTI:
            raise ValueError(f"invalid mbti: {v}")
        return v


class ChatResponse(BaseModel):
    session_id: str
    emotion: EmotionResult
    mbti: str               # 本轮生效 MBTI（取值见 config.VALID_MBTI）
    reply: str
    audio: AudioMeta
    expression: Expression
    safety_triggered: bool  # 是否被安全风控短路
    turn_count: int


class SafetyResult(BaseModel):
    hit: bool            # 命中风险词
    reply: str | None = None  # hit=True 时为固定安全回复
