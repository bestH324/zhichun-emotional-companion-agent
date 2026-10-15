"""端到端测试：对齐规划书 §7 测试方案第 6 项。"""
from fastapi.testclient import TestClient

from app.main import app


def _client():
    return TestClient(app)


def test_health():
    with _client() as c:
        assert c.get("/health").json() == {"status": "ok"}


def test_single_turn_full_response_structure():
    with _client() as c:
        r = c.post("/chat", json={"session_id": "", "text": "我今天很开心"})
        assert r.status_code == 200
        data = r.json()
        # 完整响应结构字段齐全
        assert set(data) == {
            "session_id", "emotion", "mbti", "reply",
            "audio", "expression", "safety_triggered", "turn_count",
        }
        assert data["emotion"]["emotion"] == "开心"
        assert data["emotion"]["intensity"] > 0
        assert data["mbti"] == "general"  # 初始未选，通用兜底
        assert data["reply"]  # 有回复文本
        assert data["audio"]["path"].startswith("mock://tts/")
        assert data["audio"]["duration_ms"] > 0
        assert data["expression"]["expression"] == "微笑"
        assert data["safety_triggered"] is False
        assert data["turn_count"] == 1


def test_multi_turn_conversation_and_turn_count():
    with _client() as c:
        sid = ""
        for i in range(5):
            r = c.post("/chat", json={"session_id": sid, "text": f"第{i}轮消息"})
            assert r.status_code == 200
            data = r.json()
            sid = data["session_id"]
            assert data["turn_count"] == i + 1
        # 会话续接成功，轮次累计正确


def test_safety_short_circuit_e2e():
    with _client() as c:
        r = c.post("/chat", json={"session_id": "", "text": "我想自杀"})
        data = r.json()
        assert data["safety_triggered"] is True
        assert data["turn_count"] == 0
        assert "专业" in data["reply"]


def test_initial_mbti_flow_e2e():
    with _client() as c:
        r = c.post("/chat", json={"session_id": "", "text": "你好", "initial_mbti": "ENTJ"})
        assert r.status_code == 200
        data = r.json()
        assert data["mbti"] == "ENTJ"
        # 续接时人格保持
        data2 = c.post("/chat", json={"session_id": data["session_id"], "text": "你好"}).json()
        assert data2["mbti"] == "ENTJ"


def test_invalid_initial_mbti_rejected():
    with _client() as c:
        r = c.post("/chat", json={"session_id": "", "text": "你好", "initial_mbti": "ABCD"})
        assert r.status_code == 422  # pydantic validator 校验


def test_empty_text_rejected():
    with _client() as c:
        r = c.post("/chat", json={"session_id": "", "text": ""})
        assert r.status_code == 422  # pydantic min_length 校验


def test_session_end_and_stats_e2e():
    with _client() as c:
        before = c.get("/session/stats").json()["active_sessions"]
        sid = c.post("/chat", json={"session_id": "", "text": "你好"}).json()["session_id"]
        # 新建会话后计数 +1
        assert c.get("/session/stats").json()["active_sessions"] == before + 1
        assert c.post(f"/session/{sid}/end").status_code == 200
        # 结束后回落到 before
        assert c.get("/session/stats").json()["active_sessions"] == before
        # 再结束返回 404
        assert c.post(f"/session/{sid}/end").status_code == 404
