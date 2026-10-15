"""MBTI 动态路由：固定分段切片 / 周期画像 / 众数切换 / 平局保留。"""
from collections import Counter

from app.config import CYCLE_SLICES, SLICE_SIZE
from app.llm.base import LLMClient
from app.modules.session import Session


class MBTIRouter:
    def current_mbti(self, session: Session) -> str:
        return session.current_mbti

    def set_initial(self, session: Session, mbti: str) -> None:
        """对话前可选的初始人格：设定本周期生效人格。"""
        session.initial_mbti = mbti
        session.current_mbti = mbti

    def on_turn_end(self, session: Session, llm: LLMClient) -> None:
        """回复落库、turn_count 已 +1 后调用。

        每个切片完成（turn_count % SLICE_SIZE == 0）时对该切片做一次人格画像并累积；
        本周期画像满 CYCLE_SLICES 个时取众数切换下一周期人格（平局保留当前周期）。
        """
        if session.turn_count <= 0 or session.turn_count % SLICE_SIZE != 0:
            return
        # 本切片完整 20 轮送入推断（用 slice_buffer，非截断的短期记忆）
        history = list(session.slice_buffer)
        inferred = llm.infer_mbti(history)
        session.slice_buffer.clear()  # 本片结束，重新累积下一片
        session.cycle_portraits.append(inferred)

        # 周期结束：画像满 CYCLE_SLICES 个，取众数切换
        if len(session.cycle_portraits) >= CYCLE_SLICES:
            self._switch_cycle(session)

    def _switch_cycle(self, session: Session) -> None:
        """对本周期 CYCLE_SLICES 个画像取众数；并列最高频则保留当前周期人格不变。"""
        counter = Counter(session.cycle_portraits)
        most_common = counter.most_common()
        top_freq = most_common[0][1]
        winners = [mbti for mbti, freq in most_common if freq == top_freq]
        if len(winners) == 1:
            # 唯一众数：切换
            session.current_mbti = winners[0]
        # 平局（len > 1）：保留上一周期人格（current_mbti 不变）
        session.cycle_portraits.clear()  # 进入下一周期，重新累积画像
