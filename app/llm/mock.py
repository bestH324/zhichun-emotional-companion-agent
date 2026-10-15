"""MockLLM：初赛默认后端。三原则——确定性、可断言、风格可区分。"""
import re

from app.config import MBTI_TYPES
from app.llm.base import LLMClient
from app.schemas import EmotionResult


class MockLLM(LLMClient):
    def generate(self, system_prompt: str, user_prompt: str, history: list) -> str:
        # 从 system_prompt 提取风格特征词（personality_agent 已写入 [STYLE=...]）
        style = self._extract_tag(system_prompt, "STYLE") or "温暖陪伴"
        parts = ["我理解你现在的感受。", f"我会用{style}的方式陪着你。"]
        if "[用户画像]" in user_prompt:
            parts.append("我记得你之前告诉我的事，会一直记在心里。")
        return "".join(parts)

    def infer_mbti(self, history: list) -> str:
        # 确定性映射：相同 history → 相同结果（跨进程稳定，禁用内置 hash）
        text = "".join(m.content for m in history)
        idx = sum(ord(c) for c in text) % len(MBTI_TYPES)
        return MBTI_TYPES[idx]

    def classify_emotion(self, text: str) -> EmotionResult:
        # 兜底固定返回「平静」，便于断言
        return EmotionResult(emotion="平静", intensity=0.5)

    @staticmethod
    def _extract_tag(system_prompt: str, tag: str) -> str | None:
        m = re.search(rf"\[{tag}=([^\]]+)\]", system_prompt)
        return m.group(1) if m else None
