"""LLM 工厂：按 config.LLM_BACKEND 返回实例。"""
from app.config import LLM_API_KEY, LLM_BACKEND, LLM_BASE_URL, LLM_MODEL_NAME
from app.llm.base import LLMClient
from app.llm.mock import MockLLM
from app.llm.qwen import QwenLLM


def get_llm() -> LLMClient:
    backend = LLM_BACKEND.lower()
    if backend == "mock":
        return MockLLM()
    elif backend == "qwen":
        return QwenLLM(LLM_API_KEY, LLM_BASE_URL, LLM_MODEL_NAME)
    elif backend == "openai":
        raise NotImplementedError("openai 后端尚未接入")
    raise ValueError(f"unknown LLM_BACKEND: {LLM_BACKEND}")
