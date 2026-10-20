"""语音合成：TTS_BACKEND=mock 返回占位路径（默认，兼容测试）；=edge 走 Edge-TTS 真实合成。

真实合成落地到 AUDIO_DIR，返回静态文件 URL（由 main.py 挂载 StaticFiles 服务）。
"""
import asyncio
import os
import uuid

import app.config as config
from app.schemas import AudioMeta

# 粗略：中文按 250ms/字 估算时长
_MS_PER_CHAR = 250

# 情绪 → Edge-TTS 中文音色（活泼/柔和/沉稳等差异化）
_EMOTION_VOICE = {
    "开心": "zh-CN-XiaoyiNeural",     # 活泼
    "平静": "zh-CN-XiaoxiaoNeural",   # 温柔
    "焦虑": "zh-CN-XiaoxiaoNeural",
    "悲伤": "zh-CN-XiaoxiaoNeural",
    "压力大": "zh-CN-YunxiNeural",     # 沉稳男声
    "愤怒": "zh-CN-YunyangNeural",
    "孤独": "zh-CN-XiaoxiaoNeural",
}


def synthesize(text: str, emotion: str) -> AudioMeta:
    """返回音频元数据；mock 模式或合成失败时回退占位路径，绝不抛异常。"""
    if config.TTS_BACKEND == "edge":
        path = _synthesize_edge(text, emotion)
        if path is not None:
            return AudioMeta(
                text=text,
                emotion=emotion,
                duration_ms=max(len(text) * _MS_PER_CHAR, 100),
                path=path,
            )
    # 回退：mock 占位路径
    duration_ms = max(len(text) * _MS_PER_CHAR, 100)
    path = f"mock://tts/{uuid.uuid4().hex}.wav"
    return AudioMeta(text=text, emotion=emotion, duration_ms=duration_ms, path=path)


def _synthesize_edge(text: str, emotion: str) -> str | None:
    """Edge-TTS 真实合成，成功返回静态 URL，失败返回 None（触发上层回退）。"""
    try:
        import edge_tts
    except ImportError:
        return None
    voice = _EMOTION_VOICE.get(emotion, "zh-CN-XiaoxiaoNeural")
    os.makedirs(config.AUDIO_DIR, exist_ok=True)
    filename = f"{uuid.uuid4().hex}.mp3"
    filepath = os.path.join(config.AUDIO_DIR, filename)

    async def _run():
        communicate = edge_tts.Communicate(text, voice)
        await communicate.save(filepath)

    try:
        asyncio.run(_run())
    except Exception:
        return None
    if not os.path.exists(filepath):
        return None
    return f"/static/audio/{filename}"
