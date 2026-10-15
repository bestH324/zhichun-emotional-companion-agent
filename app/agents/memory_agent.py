"""记忆管理 Agent：组装短期 + 情景召回 + 事实画像。"""
from app.modules.memory_store import MemoryStore
from app.modules.session import Session


class MemoryAgent:
    def __init__(self, store: MemoryStore):
        self.store = store

    def assemble_context(self, session: Session, query: str) -> dict:
        short_term = self.store.get_short_term(session)
        episodic = self.store.recall_episodic(session, query)
        facts = self.store.get_facts(session)
        return {
            "short_term": short_term,
            "episodic": episodic,
            "facts": facts,
        }
