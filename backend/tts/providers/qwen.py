"""
千问（通义千问3 TTS VC Realtime）声音复刻 TTS 提供商

说明：
- 声音复刻通过 `qwen-voice-enrollment` 创建音色（voice_id）。
- 语音合成通过 `qwen3-tts-vc-realtime-...` WebSocket 实时合成，回传 PCM 数据。
- 本项目返回 WAV 封装，便于浏览器播放与保存。
"""

from __future__ import annotations

import asyncio
import threading
from typing import Any, Dict, List, Optional

from ..base import BaseTTSProvider

import logging

logger = logging.getLogger(__name__)

_dashscope_lock = threading.Lock()


class QwenTTSProvider(BaseTTSProvider):
    """基于 DashScope `qwen_tts_realtime` 的声音复刻 TTS 提供商。"""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.api_key: str = config.get("api_key", "") or ""
        self.model: str = config.get("model", "qwen3-tts-vc-realtime-2025-11-27") or "qwen3-tts-vc-realtime-2025-11-27"
        self.voice_id: str = config.get("voice_id", "") or ""
        self.timeout_millis: int = int(config.get("timeout_millis", 60000) or 60000)
        self.realtime_ws_url: str = config.get("realtime_ws_url", "wss://dashscope.aliyuncs.com/api-ws/v1/realtime") or "wss://dashscope.aliyuncs.com/api-ws/v1/realtime"

    @staticmethod
    def _pcm16le_to_wav(pcm_data: bytes, sample_rate: int = 24000, channels: int = 1, bits_per_sample: int = 16) -> bytes:
        import struct

        byte_rate = sample_rate * channels * bits_per_sample // 8
        block_align = channels * bits_per_sample // 8
        data_size = len(pcm_data)
        riff_size = 36 + data_size

        header = b"".join([
            b"RIFF",
            struct.pack("<I", riff_size),
            b"WAVE",
            b"fmt ",
            struct.pack("<I", 16),
            struct.pack("<H", 1),  # PCM
            struct.pack("<H", channels),
            struct.pack("<I", sample_rate),
            struct.pack("<I", byte_rate),
            struct.pack("<H", block_align),
            struct.pack("<H", bits_per_sample),
            b"data",
            struct.pack("<I", data_size),
        ])
        return header + pcm_data

    def _synthesize_blocking(self, text: str) -> bytes:
        import base64
        import dashscope
        from dashscope.audio.qwen_tts_realtime import QwenTtsRealtime, QwenTtsRealtimeCallback, AudioFormat

        class _CollectCallback(QwenTtsRealtimeCallback):
            def __init__(self):
                self.done = threading.Event()
                self.pcm = bytearray()
                self.error: Optional[str] = None

            def on_open(self) -> None:
                pass

            def on_close(self, close_status_code, close_msg) -> None:
                if not self.done.is_set():
                    self.done.set()

            def on_event(self, response: dict) -> None:
                try:
                    event_type = response.get("type", "")
                    if event_type == "response.audio.delta":
                        delta = response.get("delta") or ""
                        if delta:
                            self.pcm.extend(base64.b64decode(delta))
                    elif event_type == "session.finished":
                        self.done.set()
                except Exception as e:  # pragma: no cover
                    self.error = str(e)
                    self.done.set()

        callback = _CollectCallback()

        with _dashscope_lock:
            prev_key = getattr(dashscope, "api_key", None)
            dashscope.api_key = self.api_key
            try:
                qwen_tts = QwenTtsRealtime(
                    model=self.model,
                    callback=callback,
                    url=self.realtime_ws_url,
                )
                qwen_tts.connect()
                qwen_tts.update_session(
                    voice=self.voice_id,
                    response_format=AudioFormat.PCM_24000HZ_MONO_16BIT,
                    mode="server_commit",
                )
                qwen_tts.append_text(text)
                qwen_tts.finish()

                timeout_seconds = max(1.0, float(self.timeout_millis) / 1000.0)
                callback.done.wait(timeout_seconds)
                try:
                    qwen_tts.close()
                except Exception:
                    pass

                if callback.error:
                    raise RuntimeError(f"千问TTS 回调处理失败: {callback.error}")
                if not callback.pcm:
                    raise RuntimeError("千问TTS 返回音频为空或超时")
                return self._pcm16le_to_wav(bytes(callback.pcm), sample_rate=24000, channels=1, bits_per_sample=16)
            finally:
                dashscope.api_key = prev_key

    async def synthesize(self, text: str, voice: Optional[str] = None) -> bytes:
        if not self.api_key:
            raise ValueError("千问TTS API Key 未配置（tts.qwen.api_key）")
        if not self.voice_id:
            raise ValueError("千问TTS 未配置声音复刻音色ID（tts.qwen.voice_id），请先上传音频并创建音色")

        text = (text or "").strip()
        if not text:
            return b""
        wav_data = await asyncio.to_thread(self._synthesize_blocking, text)
        logger.info("千问TTS 合成成功：text_len=%s audio_size=%s model=%s", len(text), len(wav_data), self.model)
        return wav_data

    async def get_voices(self) -> List[Dict[str, str]]:
        if self.voice_id:
            return [{"name": self.voice_id, "description": "声音复刻音色"}]
        return []

    async def test_connection(self) -> bool:
        if not self.api_key or not self.voice_id:
            return False
        try:
            audio = await self.synthesize("你好，这是一个语音合成测试。")
            return bool(audio)
        except Exception as e:
            logger.error("千问TTS 连接测试失败: %s", str(e))
            return False
