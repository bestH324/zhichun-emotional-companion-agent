"""API 鉴权：API_TOKEN 为空时关闭（本地/测试），否则校验 Bearer 或 X-API-Key 头。"""
from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

import app.config as config

_bearer = HTTPBearer(auto_error=False)


def require_token(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    x_api_key: str | None = Header(default=None),
) -> None:
    """依赖注入：校验请求鉴权。API_TOKEN 为空则跳过。

    支持两种携带方式：Authorization: Bearer <token> 或 X-API-Key: <token>。
    动态读取 config.API_TOKEN（便于测试 monkeypatch 与未来热更新）。
    """
    token = config.API_TOKEN
    if not token:
        return
    provided = credentials.credentials if credentials is not None else None
    provided = provided or x_api_key
    if provided != token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid or missing token",
        )
