"""QwenLLM：真实后端占位，提交时填充真实 HTTP 调用。"""
from app.llm.base import LLMClient


class QwenLLM(LLMClient):
    def __init__(self, api_key: str = "", base_url: str = "", model_name: str = ""):
        self.api_key = api_key
        self.base_url = base_url
        self.model_name = model_name

    def generate(self, system_prompt: str, user_prompt: str, history: list) -> str:
        raise NotImplementedError("初赛使用 Mock 后端，提交时在此接入真实 Qwen")

    def infer_mbti(self, history: list) -> str:
        raise NotImplementedError("初赛使用 Mock 后端")

    def classify_emotion(self, text: str):
        raise NotImplementedError("初赛使用 Mock 后端")
