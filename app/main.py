"""FastAPI 入口 + 路由：仅编排，不含业务逻辑。"""
import os
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.agents.router_agent import process_chat
from app.auth import require_token
from app.config import AUDIO_DIR
from app.modules.session import session_manager
from app.schemas import ChatRequest, ChatResponse

# 静态资源根目录（前端页面 + 音频文件）
STATIC_DIR = os.path.join(os.path.dirname(__file__), "..", "static")
STATIC_DIR = os.path.abspath(STATIC_DIR)


@asynccontextmanager
async def lifespan(_: FastAPI):
    # 启动后台 TTL 清理线程
    session_manager.start_cleanup()
    yield
    # 优雅关闭：停止清理线程
    session_manager.stop_cleanup()


app = FastAPI(title="芝春情感陪伴数字人", version="2.0", lifespan=lifespan)

# 静态文件：前端页面与音频（不鉴权）
os.makedirs(os.path.join(STATIC_DIR, "audio"), exist_ok=True)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/")
def index() -> FileResponse:
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/chat", response_model=ChatResponse, dependencies=[Depends(require_token)])
def chat(req: ChatRequest) -> ChatResponse:
    return process_chat(req.session_id, req.text, req.initial_mbti)


@app.post("/session/{session_id}/end", dependencies=[Depends(require_token)])
def end_session(session_id: str) -> dict:
    ended = session_manager.end(session_id)
    if not ended:
        raise HTTPException(status_code=404, detail="session not found")
    return {"ended": True}


@app.get("/session/stats", dependencies=[Depends(require_token)])
def session_stats() -> dict:
    return {"active_sessions": session_manager.count()}
