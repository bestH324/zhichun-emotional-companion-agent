"""Mock TTS：情绪标签 → mock 音频元数据。"""
import uuid

from app.schemas import AudioMeta

# 粗略：中文按 250ms/字 估算时长
_MS_PER_CHAR = 250


def synthesize(text: str, emotion: str) -> AudioMeta:
    duration_ms = max(len(text) * _MS_PER_CHAR, 100)
    path = f"mock://tts/{uuid.uuid4().hex}.wav"
    return AudioMeta(text=text, emotion=emotion, duration_ms=duration_ms, path=path)
