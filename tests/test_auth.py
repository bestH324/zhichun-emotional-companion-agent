"""鉴权测试：API_TOKEN 空则跳过；非空则校验 Bearer / X-API-Key。"""
import importlib

from fastapi.testclient import TestClient

import app.config as config
from app.main import app


def _client():
    return TestClient(app)


def test_no_token_disabled(monkeypatch):
    """API_TOKEN 为空 → 无需鉴权，直接访问。"""
    monkeypatch.setattr(config, "API_TOKEN", "")
    with _client() as c:
        r = c.post("/chat", json={"session_id": "", "text": "你好"})
        assert r.status_code == 200


def test_bearer_token_ok(monkeypatch):
    monkeypatch.setattr(config, "API_TOKEN", "secret123")
    with _client() as c:
        r = c.post(
            "/chat",
            json={"session_id": "", "text": "你好"},
            headers={"Authorization": "Bearer secret123"},
        )
        assert r.status_code == 200


def test_wrong_token_401(monkeypatch):
    monkeypatch.setattr(config, "API_TOKEN", "secret123")
    with _client() as c:
        r = c.post("/chat", json={"session_id": "", "text": "你好"})
        assert r.status_code == 401


def test_x_api_key_ok(monkeypatch):
    monkeypatch.setattr(config, "API_TOKEN", "secret123")
    with _client() as c:
        r = c.post(
            "/chat",
            json={"session_id": "", "text": "你好"},
            headers={"X-API-Key": "secret123"},
        )
        assert r.status_code == 200


def test_health_and_static_not_protected(monkeypatch):
    monkeypatch.setattr(config, "API_TOKEN", "secret123")
    with _client() as c:
        assert c.get("/health").status_code == 200
        assert c.get("/").status_code == 200
