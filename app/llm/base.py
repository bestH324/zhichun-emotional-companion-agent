"""LLM 抽象基类：业务代码唯一依赖此接口，绝不 import 具体实现。"""
from abc import ABC, abstractmethod

from app.schemas import EmotionResult, Message


class LLMClient(ABC):
    @abstractmethod
    def generate(self, system_prompt: str, user_prompt: str, history: list[Message]) -> str:
        """生成人格化回复，返回纯文本。"""

    @abstractmethod
    def infer_mbti(self, history: list[Message]) -> str:
        """对切片对话推断 MBTI，返回 config.VALID_MBTI 取值之一。"""

    @abstractmethod
    def classify_emotion(self, text: str) -> EmotionResult:
        """情感识别兜底，返回 EmotionResult。"""
