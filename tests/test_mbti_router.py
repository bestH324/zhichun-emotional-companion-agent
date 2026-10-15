"""MBTI 周期路由细粒度测试：切片画像 / 周期众数切换 / 平局保留。"""
from app.config import CYCLE_SLICES, SLICE_SIZE
from app.llm.base import LLMClient
from app.modules.mbti_router import MBTIRouter
from app.modules.session import Session
from app.schemas import EmotionResult, Message


class FakeLLM(LLMClient):
    """可控推断结果的 LLM，记录每次推断收到的 history 长度。"""

    def __init__(self, infer_results):
        self._results = list(infer_results)
        self.calls = 0
        self.history_lengths: list[int] = []

    def infer_mbti(self, history) -> str:
        self.history_lengths.append(len(history))
        idx = min(self.calls, len(self._results) - 1)
        self.calls += 1
        return self._results[idx]

    def generate(self, system_prompt, user_prompt, history) -> str:
        return ""

    def classify_emotion(self, text) -> EmotionResult:
        return EmotionResult(emotion="平静", intensity=0.5)


def _turn(session: Session, router: MBTIRouter, llm: LLMClient) -> None:
    """模拟一轮结束：累积 user+assistant 两条、计数 +1、触发 on_turn_end。"""
    session.slice_buffer.append(Message(role="user", content="u"))
    session.slice_buffer.append(Message(role="assistant", content="a"))
    session.turn_count += 1
    router.on_turn_end(session, llm)


def _new_session() -> Session:
    return Session(session_id="s")


# 1. 不足 20 轮不切片、不画像、沿用初始人格
def test_no_infer_before_20_and_keeps_initial():
    llm = FakeLLM(["INTJ"])
    router = MBTIRouter()
    session = _new_session()
    router.set_initial(session, "INFP")

    for _ in range(19):
        _turn(session, router, llm)

    assert session.cycle_portraits == []         # 不足 20 轮不画像
    assert llm.calls == 0                        # 未触发推断
    assert session.current_mbti == "INFP"        # 沿用初始人格
    assert session.initial_mbti == "INFP"


# 2. 固定分段：第 20/40/60 轮各画像一次；每个切片恰好画像一次
def test_portrait_fires_only_at_slice_boundaries():
    llm = FakeLLM(["INTJ", "INFP", "ENTJ"])
    router = MBTIRouter()
    session = _new_session()

    for _ in range(60):
        _turn(session, router, llm)

    assert llm.calls == 3                        # 恰好 20/40/60 三次画像
    assert session.cycle_portraits == ["INTJ", "INFP", "ENTJ"]


# 3. 取整片而非近 20 轮：第 20 轮画像拿到完整 20 轮（40 条）
def test_portrait_uses_full_20_rounds_not_truncated():
    llm = FakeLLM(["INTJ"])
    router = MBTIRouter()
    session = _new_session()

    for _ in range(SLICE_SIZE):
        _turn(session, router, llm)

    assert llm.history_lengths == [SLICE_SIZE * 2]  # 20 轮 × 2 条


# 4. 周期内人格固定：前 5 个切片期间，current_mbti 始终是初始人格
def test_initial_mbti_fixed_for_first_cycle():
    llm = FakeLLM(["INTJ", "INFP", "ENTJ", "ISTJ", "ENFP"])
    router = MBTIRouter()
    session = _new_session()
    router.set_initial(session, "ENTJ")

    # 跑完 5 个切片（100 轮），期间人格不变
    for _ in range(SLICE_SIZE * CYCLE_SLICES):
        _turn(session, router, llm)
        assert session.current_mbti == "ENTJ"


# 5a. 周期结束取众数切换：5 个画像里 4 个 INFP → 切换到 INFP
def test_cycle_switch_by_majority():
    llm = FakeLLM(["INFP", "INFP", "INFP", "INTJ", "INFP"])
    router = MBTIRouter()
    session = _new_session()
    router.set_initial(session, "ENTJ")

    for _ in range(SLICE_SIZE * CYCLE_SLICES):  # 100 轮
        _turn(session, router, llm)

    assert session.current_mbti == "INFP"        # 众数切换
    assert session.cycle_portraits == []         # 进入下一周期，重新累积


# 5b. 平局保留上一周期人格
def test_cycle_tie_keeps_current():
    # 2 个 A、2 个 B、1 个 C → 并列最高频，保留当前周期人格
    llm = FakeLLM(["INTJ", "INTJ", "INFP", "INFP", "ENTJ"])
    router = MBTIRouter()
    session = _new_session()
    router.set_initial(session, "ENTP")

    for _ in range(SLICE_SIZE * CYCLE_SLICES):
        _turn(session, router, llm)

    assert session.current_mbti == "ENTP"        # 平局保留上一周期
    assert session.cycle_portraits == []         # 画像已清空


# 6. 多周期连续切换：第 2 个周期基于新画像再次切换
def test_multi_cycle_switching():
    # 周期1 画像：5 个 ISTJ → 切 ISTJ；周期2 画像：5 个 ENFP → 切 ENFP
    llm = FakeLLM(["ISTJ"] * 5 + ["ENFP"] * 5)
    router = MBTIRouter()
    session = _new_session()
    router.set_initial(session, "general")

    for _ in range(SLICE_SIZE * CYCLE_SLICES):      # 周期 1
        _turn(session, router, llm)
    assert session.current_mbti == "ISTJ"

    for _ in range(SLICE_SIZE * CYCLE_SLICES):      # 周期 2
        _turn(session, router, llm)
    assert session.current_mbti == "ENFP"
