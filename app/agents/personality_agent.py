"""人格对话 Agent：按生效 MBTI 加载 Prompt，调用 LLM 生成回复。"""
from app.llm.base import LLMClient
from app.modules.session import Session
from app.prompts.mbti_prompts import get_mbti_prompt


class PersonalityAgent:
    def __init__(self, llm: LLMClient):
        self.llm = llm

    def generate_reply(self, session: Session, context: dict, user_text: str) -> str:
        system_prompt = get_mbti_prompt(session.current_mbti)
        user_prompt = self._build_user_prompt(context, user_text)
        history = list(context["short_term"])
        return self.llm.generate(system_prompt, user_prompt, history)

    @staticmethod
    def _build_user_prompt(context: dict, user_text: str) -> str:
        parts = [f"用户说：{user_text}"]
        facts = context["facts"]
        if facts:
            facts_str = "；".join(f"{k}：{v}" for k, v in facts.items())
            parts.append(f"[用户画像] {facts_str}")
        episodic = context["episodic"]
        if episodic:
            parts.append("[相关回忆] " + "；".join(episodic))
        return "\n".join(parts)
