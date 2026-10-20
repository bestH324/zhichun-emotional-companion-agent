"""TTS 测试：mock 模式返回占位路径（默认，兼容历史行为）。"""
import app.config as config
from app.modules.tts import synthesize


def test_mock_tts_returns_placeholder(monkeypatch):
    monkeypatch.setattr(config, "TTS_BACKEND", "mock")
    meta = synthesize("你好", "平静")
    assert meta.path.startswith("mock://tts/")
    assert meta.duration_ms > 0
    assert meta.emotion == "平静"


def test_edge_failure_falls_back_to_mock(monkeypatch):
    """edge 模式但无网络/库失败时，回退 mock 路径，绝不抛异常。"""
    monkeypatch.setattr(config, "TTS_BACKEND", "edge")
    # 即便 edge-tts 合成失败（无网络），也应回退占位路径
    meta = synthesize("你好", "平静")
    assert meta.path.startswith("mock://tts/") or meta.path.startswith("/static/audio/")
    assert meta.duration_ms > 0
