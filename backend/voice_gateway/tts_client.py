"""TTS 客户端封装（Realtime 优先，兼容回退）。"""

from __future__ import annotations

import asyncio
import base64
import json
import logging
from typing import AsyncGenerator, Optional
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

import aiohttp

from backend.core.bot import Bot

from .config import VoiceGatewayConfig

logger = logging.getLogger(__name__)


class TTSClient:
    """将文本切片合成为音频帧。"""

    def __init__(self, bot: Bot, cfg: VoiceGatewayConfig):
        self.bot = bot
        self.cfg = cfg
        self._clear_requested = False
        self._lock = asyncio.Lock()
        self._ws: Optional[aiohttp.ClientWebSocketResponse] = None
        self._session: Optional[aiohttp.ClientSession] = None
        self._reader_task: Optional[asyncio.Task] = None
        self._audio_queue: asyncio.Queue[bytes | None] = asyncio.Queue()

    @property
    def is_connected(self) -> bool:
        if self._ws is None:
            return False
        if self._ws.closed:
            return False
        try:
            return not self._ws._writer.transport.is_closing()
        except Exception:
            return False

    def _get_bot_tts_qwen_cfg(self) -> dict:
        tts_manager = getattr(self.bot, "tts_manager", None)
        if not tts_manager:
            return {}

        tts_config = getattr(tts_manager, "config", None)
        if not tts_config:
            return {}

        # TTSManager.config 是 Pydantic 模型（TTSConfig），兼容旧字典结构。
        if hasattr(tts_config, "qwen") and isinstance(getattr(tts_config, "qwen"), dict):
            return getattr(tts_config, "qwen")

        if isinstance(tts_config, dict):
            qwen_cfg = tts_config.get("qwen", {})
            return qwen_cfg if isinstance(qwen_cfg, dict) else {}

        if hasattr(tts_config, "model_dump"):
            dumped = tts_config.model_dump()
            qwen_cfg = dumped.get("qwen", {}) if isinstance(dumped, dict) else {}
            return qwen_cfg if isinstance(qwen_cfg, dict) else {}

        return {}

    def _resolve_api_key(self) -> str:
        if self.cfg.tts.api_key:
            return self.cfg.tts.api_key
        qwen_cfg = self._get_bot_tts_qwen_cfg()
        return qwen_cfg.get("api_key", "")

    def _build_ws_url_with_model(self) -> str:
        raw_url = (self.cfg.tts.ws_url or "").strip()
        if not raw_url:
            return raw_url
        try:
            parsed = urlparse(raw_url)
            query = dict(parse_qsl(parsed.query, keep_blank_values=True))
            if "model" not in query and self.cfg.tts.model:
                query["model"] = self.cfg.tts.model
            rebuilt = parsed._replace(query=urlencode(query))
            return urlunparse(rebuilt)
        except Exception:
            return raw_url

    async def connect(self) -> bool:
        if not (self.cfg.tts.enabled and self.cfg.tts.realtime_enabled):
            return False
        api_key = self._resolve_api_key()
        if not api_key:
            return False
        try:
            headers = {"Authorization": f"Bearer {api_key}"}
            self._session = aiohttp.ClientSession(headers=headers)
            ws_url = self._build_ws_url_with_model()
            self._ws = await self._session.ws_connect(ws_url)

            voice_id = self.cfg.tts.voice
            if not voice_id:
                qwen_cfg = self._get_bot_tts_qwen_cfg()
                voice_id = qwen_cfg.get("voice_id") or qwen_cfg.get("preferred_name", "")
            logger.info("TTS realtime connect: model=%s voice=%s", self.cfg.tts.model, voice_id)

            await self._ws.send_json({
                "type": "session.update",
                "session": {
                    "voice": voice_id,
                    "response_format": "pcm",
                    "sample_rate": self.cfg.audio.output_sample_rate,
                    "mode": "server_commit",
                },
            })

            self._reader_task = asyncio.create_task(self._reader_loop())
            return True
        except Exception as exc:
            logger.warning("TTS realtime connect failed: %s", exc)
            await self._drop_realtime()
            return False

    async def _reader_loop(self) -> None:
        if self._ws is None:
            return
        try:
            async for msg in self._ws:
                if msg.type != aiohttp.WSMsgType.TEXT:
                    continue
                try:
                    data = json.loads(msg.data)
                except Exception:
                    continue
                event_type = data.get("type", "")
                if event_type == "response.audio.delta":
                    delta = data.get("delta") or ""
                    if delta:
                        await self._audio_queue.put(base64.b64decode(delta))
                elif event_type in {"response.done", "session.finished", "error"}:
                    await self._audio_queue.put(None)
        except Exception as exc:
            logger.warning("TTS reader loop error: %s", exc)
        finally:
            await self._audio_queue.put(None)

    async def _synthesize_realtime(self, text: str) -> AsyncGenerator[bytes, None]:
        if not self.is_connected:
            return

        await self._ws.send_json({
            "type": "input_text_buffer.append",
            "text": text,
        })
        await self._ws.send_json({"type": "input_text_buffer.commit"})

        while True:
            try:
                chunk = await asyncio.wait_for(self._audio_queue.get(), timeout=15.0)
            except asyncio.TimeoutError as exc:
                raise RuntimeError("tts realtime response timeout") from exc
            if chunk is None:
                break
            if self._clear_requested:
                return
            yield chunk

    async def _drop_realtime(self) -> None:
        if self._reader_task and not self._reader_task.done():
            self._reader_task.cancel()
            try:
                await self._reader_task
            except asyncio.CancelledError:
                pass
            except Exception:
                pass
        self._reader_task = None

        if self._ws is not None:
            try:
                await self._ws.close()
            except Exception:
                pass
            self._ws = None

        if self._session is not None:
            try:
                await self._session.close()
            except Exception:
                pass
            self._session = None

        while not self._audio_queue.empty():
            try:
                self._audio_queue.get_nowait()
            except asyncio.QueueEmpty:
                break

    async def _synthesize_fallback(self, text: str, user_id: str, frame_bytes: int) -> AsyncGenerator[bytes, None]:
        try:
            tts_manager = self.bot._get_user_tts_manager(user_id) or self.bot.tts_manager
            provider_name = type(getattr(tts_manager, "provider", None)).__name__ if tts_manager else "None"
            logger.info("TTS fallback provider=%s user_id=%s text_len=%s", provider_name, user_id, len(text or ""))
        except Exception:
            pass
        audio = await self.bot.synthesize_speech(text, user_id=user_id)
        if not audio:
            return
        for i in range(0, len(audio), frame_bytes):
            if self._clear_requested:
                return
            yield audio[i:i + frame_bytes]

    async def synthesize_stream(self, text: str, user_id: str, frame_bytes: int) -> AsyncGenerator[bytes, None]:
        async with self._lock:
            self._clear_requested = False
            # 语音网关模式下，realtime_enabled=True 时严格要求走 realtime，
            # 避免 silently 回退导致音色偏差。
            if self.cfg.tts.realtime_enabled:
                if not self.is_connected:
                    raise RuntimeError("tts realtime not connected")
                async for chunk in self._synthesize_realtime(text):
                    yield chunk
                return

            async for chunk in self._synthesize_fallback(text, user_id, frame_bytes):
                yield chunk

    async def clear(self) -> None:
        async with self._lock:
            self._clear_requested = True
            if self.is_connected:
                try:
                    await self._ws.send_json({"type": "response.cancel"})
                except Exception:
                    pass

    async def close(self) -> None:
        await self._drop_realtime()
