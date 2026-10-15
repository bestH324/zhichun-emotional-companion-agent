"""FastAPI 入口 + 路由：仅编排，不含业务逻辑。"""
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException

from app.agents.router_agent import process_chat
from app.modules.session import session_manager
from app.schemas import ChatRequest, ChatResponse


@asynccontextmanager
async def lifespan(_: FastAPI):
    # 启动后台 TTL 清理线程
    session_manager.start_cleanup()
    yield
    # 优雅关闭：停止清理线程
    session_manager.stop_cleanup()


app = FastAPI(title="芝春情感陪伴数字人", version="1.0", lifespan=lifespan)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest) -> ChatResponse:
    return process_chat(req.session_id, req.text, req.initial_mbti)


@app.post("/session/{session_id}/end")
def end_session(session_id: str) -> dict:
    ended = session_manager.end(session_id)
    if not ended:
        raise HTTPException(status_code=404, detail="session not found")
    return {"ended": True}


@app.get("/session/stats")
def session_stats() -> dict:
    return {"active_sessions": session_manager.count()}
