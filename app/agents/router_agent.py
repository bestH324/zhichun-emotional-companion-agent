"""整体调度 Agent：严格按规划书 §3.2 数据流 1~10 步编排，唯一实现数据流入口。"""
from app.agents.memory_agent import MemoryAgent
from app.agents.personality_agent import PersonalityAgent
from app.config import DB_PATH, VALID_MBTI
from app.llm.factory import get_llm
from app.modules.avatar import render_expression
from app.modules.emotion import recognize_emotion
from app.modules.mbti_router import MBTIRouter
from app.modules.memory_store import MemoryStore
from app.modules.safety import check_safety
from app.modules.session import Session, SessionManager, session_manager
from app.modules.tts import synthesize
from app.schemas import ChatResponse, EmotionResult, Message

# ===== 只读依赖（进程级单例，无业务可变状态，线程安全）=====
_llm = get_llm()
_store = MemoryStore(db_path=DB_PATH or None)
_memory_agent = MemoryAgent(_store)
_personality_agent = PersonalityAgent(_llm)
_mbti_router = MBTIRouter()


def process_chat(session_id: str, text: str, initial_mbti: str | None = None,
                 manager: SessionManager = session_manager) -> ChatResponse:
    """一轮交互的完整编排。返回统一响应结构。

    单会话内顺序处理：对同一 session 持锁串行执行，不同 session 之间并行（规划书 §4.8.2）。
    initial_mbti 仅在会话尚未开始对话（turn_count == 0）时生效，续接时忽略。
    """
    # 1. 接收用户文本 + 会话 ID（空则服务端生成 uuid4；非空仅在命中未过期会话时续接）
    if initial_mbti is not None and initial_mbti not in VALID_MBTI:
        raise ValueError(f"invalid mbti: {initial_mbti}")
    session = manager.get_or_create(session_id)
    with session.lock:
        # 初次对话前可选初始人格：仅在尚未有任何对话时应用
        if initial_mbti is not None and session.turn_count == 0:
            _mbti_router.set_initial(session, initial_mbti)
        return _process_locked(session, text, manager)


def _process_locked(session: Session, text: str, manager: SessionManager) -> ChatResponse:
    """锁内执行的数据流 2~10 步（调用方已持有 session.lock）。"""

    # 2. 安全风控前置检查：命中短路，不进入记忆与生成
    safety = check_safety(text)
    if safety.hit:
        return ChatResponse(
            session_id=session.session_id,
            emotion=EmotionResult(emotion="平静", intensity=0.0),
            mbti=session.current_mbti,
            reply=safety.reply or "",
            audio=synthesize(safety.reply or "", "平静"),
            expression=render_expression("平静"),
            safety_triggered=True,
            turn_count=session.turn_count,
        )

    # 3. 情感识别：规则为主 + Mock 兜底
    emotion = recognize_emotion(text, _llm)

    # 本轮生效 MBTI（生成前取，切片结果影响下一轮）
    effective_mbti = _mbti_router.current_mbti(session)

    # 6. 记忆检索：组装短期 + 情景召回 + 事实画像
    context = _memory_agent.assemble_context(session, text)

    # 7. 人格对话生成
    reply = _personality_agent.generate_reply(session, context, text)

    # 8. 回复落库并结算轮次（user + assistant 两条；事实提取）
    _store.add_message(session, Message(role="user", content=text))
    _store.extract_facts(session, text)
    _store.add_message(session, Message(role="assistant", content=reply))
    session.turn_count += 1

    # 持久化会话元数据（turn_count / current_mbti / facts），纯内存模式为空操作
    manager.save(session)

    # 5. MBTI 切片/投票（结算后触发，仅切片完成时推断）
    _mbti_router.on_turn_end(session, _llm)

    # 9. 情绪驱动：TTS(mock) + 渲染(mock)
    audio = synthesize(reply, emotion.emotion)
    expression = render_expression(emotion.emotion)

    # 10. 返回统一响应结构
    return ChatResponse(
        session_id=session.session_id,
        emotion=emotion,
        mbti=effective_mbti,
        reply=reply,
        audio=audio,
        expression=expression,
        safety_triggered=False,
        turn_count=session.turn_count,
    )


def set_initial_mbti(session_id: str, mbti: str, manager: SessionManager = session_manager) -> str:
    """对话前可选初始人格：设定本周期生效人格。"""
    if mbti not in VALID_MBTI:
        raise ValueError(f"invalid mbti: {mbti}, must be one of {VALID_MBTI}")
    session = manager.get_or_create(session_id)
    with session.lock:
        _mbti_router.set_initial(session, mbti)
        return session.current_mbti
