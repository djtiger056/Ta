"""Omni 客户端封装（Realtime 优先，兼容回退）。"""

from __future__ import annotations

import asyncio
import base64
import json
import logging
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse
from typing import AsyncGenerator, Dict, Optional

import aiohttp

from backend.config import config
from backend.providers import get_provider

from .config import VoiceGatewayOmniConfig

logger = logging.getLogger(__name__)


class OmniTransportError(Exception):
    """Omni realtime 连接不可用。"""


class OmniClient:
    """统一 Omni 接口：支持实时音频输入与文本增量输出。"""

    def __init__(self, omni_cfg: VoiceGatewayOmniConfig):
        llm_cfg = config.llm_config or {}
        self.omni_cfg = omni_cfg
        provider_name = llm_cfg.get("provider", "openai")
        self.provider = get_provider(provider_name, llm_config=llm_cfg)

        self._ws: Optional[aiohttp.ClientWebSocketResponse] = None
        self._session: Optional[aiohttp.ClientSession] = None
        self._reader_task: Optional[asyncio.Task] = None
        self._queue: asyncio.Queue = asyncio.Queue()
        self._last_input_text: str = ""
        self._connect_ready = asyncio.Event()
        self._connect_error: str = ""

    @staticmethod
    def _extract_error_message(data: Dict[str, object]) -> str:
        error_obj = data.get("error")
        if isinstance(error_obj, dict):
            return str(error_obj.get("message") or "unknown error")
        return str(error_obj or data.get("message") or "unknown error")

    @staticmethod
    def _is_ignorable_runtime_error(data: Dict[str, object]) -> bool:
        """
        可忽略的运行时错误（常见于 response.cancel 竞态）：
        当前无活动响应时发送 response.cancel，服务端会返回该错误。
        """
        message = OmniClient._extract_error_message(data).lower()
        return "none active response" in message

    @property
    def is_connected(self) -> bool:
        """检查连接是否可用（不仅是未关闭，还要确保可写入）。"""
        if self._ws is None:
            return False
        # 检查 WebSocket 是否关闭或正在关闭
        if self._ws.closed:
            return False
        # aiohttp WebSocket 在 closing 状态下也不能写入
        try:
            return not self._ws._writer.transport.is_closing()
        except (AttributeError, RuntimeError):
            # 如果无法访问底层 transport，保守地认为不可用
            return False

    def _resolve_api_key(self) -> str:
        if self.omni_cfg.api_key:
            return self.omni_cfg.api_key
        llm_cfg = config.llm_config or {}
        provider_name = llm_cfg.get("provider", "")
        provider_cfg = llm_cfg.get(provider_name, {}) if isinstance(llm_cfg, dict) else {}
        return provider_cfg.get("api_key") or llm_cfg.get("api_key", "")

    def _build_ws_url_with_model(self) -> str:
        """
        DashScope realtime 要求在 WS URL query 上带 model 参数。
        若配置里已存在 model 则不覆盖。
        """
        raw_url = (self.omni_cfg.ws_url or "").strip()
        if not raw_url:
            return raw_url

        try:
            parsed = urlparse(raw_url)
            query = dict(parse_qsl(parsed.query, keep_blank_values=True))
            if "model" not in query and self.omni_cfg.model:
                query["model"] = self.omni_cfg.model
            rebuilt = parsed._replace(query=urlencode(query))
            return urlunparse(rebuilt)
        except Exception:
            return raw_url

    async def connect(self, instructions: str = "") -> bool:
        if self.is_connected:
            return True
        if not self.omni_cfg.realtime_enabled:
            return False

        api_key = self._resolve_api_key()
        if not api_key:
            return False

        # 重连时清空旧队列，避免旧消息干扰
        self._connect_ready = asyncio.Event()
        self._connect_error = ""
        while not self._queue.empty():
            try:
                self._queue.get_nowait()
            except asyncio.QueueEmpty:
                break

        try:
            headers = {
                "Authorization": f"Bearer {api_key}",
            }
            timeout = aiohttp.ClientTimeout(total=max(5, self.omni_cfg.request_timeout_seconds))
            self._session = aiohttp.ClientSession(timeout=timeout, headers=headers)
            ws_url = self._build_ws_url_with_model()
            logger.info("Connecting to Omni WebSocket: %s", ws_url)

            self._ws = await self._session.ws_connect(ws_url)
            self._reader_task = asyncio.create_task(self._reader_loop())
            logger.info("Omni WebSocket connected, sending session.update")

            session_payload: Dict[str, object] = {
                "modalities": ["text"],
                "instructions": instructions or "",
                "input_audio_format": "pcm16",
                "input_audio_transcription": {
                    "model": self.omni_cfg.input_transcription_model,
                },
            }
            turn_detection_type = (self.omni_cfg.turn_detection_type or "").strip().lower()
            # DashScope 手动轮次模式需要 turn_detection=null。
            if turn_detection_type in {"none", "null", "manual", "off"}:
                session_payload["turn_detection"] = None
            elif turn_detection_type:
                session_payload["turn_detection"] = {
                    "type": self.omni_cfg.turn_detection_type,
                    "threshold": self.omni_cfg.vad_threshold,
                    "prefix_padding_ms": self.omni_cfg.vad_prefix_padding_ms,
                    "silence_duration_ms": self.omni_cfg.vad_silence_duration_ms,
                }

            session_update = {
                "type": "session.update",
                "session": session_payload,
            }
            await self._ws.send_json(session_update)

            # 只有收到会话确认事件才判定连接成功，避免“已连上但立即被上游断开”的假成功
            try:
                await asyncio.wait_for(self._connect_ready.wait(), timeout=5.0)
            except asyncio.TimeoutError:
                self._connect_error = "session.update handshake timeout"

            if self._connect_error:
                logger.error("Omni handshake failed: %s", self._connect_error)
                await self.close()
                return False
            if not self.is_connected:
                logger.error("Omni websocket closed during handshake")
                await self.close()
                return False

            logger.info("Omni client connected successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to Omni service: {e}")
            # 清理失败的连接
            await self.close()
            return False

    async def _reader_loop(self) -> None:
        if self._ws is None:
            return
        try:
            async for msg in self._ws:
                if msg.type == aiohttp.WSMsgType.TEXT:
                    try:
                        data = json.loads(msg.data)
                    except Exception:
                        continue
                    event_type = data.get("type", "")
                    if event_type in {"session.created", "session.updated", "response.created", "response.done", "response.text.done"}:
                        logger.info("Omni event: %s", event_type)
                    if event_type in {"session.created", "session.updated"}:
                        self._connect_ready.set()
                    elif event_type == "error":
                        # 运行期可预期错误（如 cancel 竞态）不应打断后续轮次。
                        if self._is_ignorable_runtime_error(data):
                            logger.info("Omni event ignored runtime error: %s", data)
                            continue

                        logger.warning("Omni event error: %s", data)
                        error_data = data.get("error")
                        if isinstance(error_data, dict):
                            error_msg = str(error_data.get("message") or "unknown error")
                            error_code = error_data.get("code")
                            if error_code:
                                parsed_error = f"{error_code}: {error_msg}"
                            else:
                                parsed_error = error_msg
                        else:
                            parsed_error = str(error_data or data.get("message") or "unknown error")

                        if not self._connect_ready.is_set():
                            self._connect_error = parsed_error
                            self._connect_ready.set()
                    await self._queue.put(data)
                    if event_type == "conversation.item.input_audio_transcription.completed":
                        self._last_input_text = (data.get("transcript") or "").strip()
                elif msg.type in {aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.ERROR}:
                    logger.warning(
                        "Omni websocket closing: msg_type=%s close_code=%s exception=%s",
                        msg.type,
                        self._ws.close_code,
                        self._ws.exception(),
                    )
                    if not self._connect_ready.is_set():
                        if not self._connect_error:
                            self._connect_error = f"websocket closed during connect (code={self._ws.close_code})"
                        self._connect_ready.set()
                    break
        finally:
            logger.warning("Omni reader loop ended: close_code=%s", self._ws.close_code if self._ws else None)
            if not self._connect_ready.is_set():
                if not self._connect_error:
                    self._connect_error = "websocket closed unexpectedly"
                self._connect_ready.set()
            await self._queue.put({"type": "_ws_closed"})

    async def send_audio(self, pcm_data: bytes) -> None:
        if not self.is_connected:
            raise OmniTransportError("omni websocket not connected")
        payload = {
            "type": "input_audio_buffer.append",
            "audio": base64.b64encode(pcm_data).decode("utf-8"),
        }
        try:
            # 发送前再次检查，防止在准备 payload 期间连接关闭
            if not self.is_connected:
                raise OmniTransportError("omni websocket closed before send")
            await self._ws.send_json(payload)
        except OmniTransportError:
            raise
        except Exception as exc:
            raise OmniTransportError(f"failed to send audio to omni websocket: {exc}") from exc

    async def commit_audio(self) -> None:
        if not self.is_connected:
            raise OmniTransportError("omni websocket not connected")
        try:
            # 发送前再次检查连接状态
            if not self.is_connected:
                raise OmniTransportError("omni websocket closed before commit")
            await self._ws.send_json({"type": "input_audio_buffer.commit"})
            # 两次发送之间再检查一次
            if not self.is_connected:
                raise OmniTransportError("omni websocket closed during commit")
            await self._ws.send_json({"type": "response.create", "response": {"modalities": ["text"]}})
        except OmniTransportError:
            raise
        except Exception as exc:
            raise OmniTransportError(f"failed to commit audio to omni websocket: {exc}") from exc

    async def cancel_response(self) -> None:
        if not self.is_connected:
            return
        try:
            await self._ws.send_json({"type": "response.cancel"})
        except Exception:
            return

    async def stream_response(self, fallback_prompt: str, context: Optional[str] = None) -> AsyncGenerator[str, None]:
        if self._ws:
            collected: list[str] = []
            while True:
                data = await self._queue.get()
                event_type = data.get("type", "")
                if event_type == "response.text.delta":
                    delta = data.get("delta") or ""
                    if delta:
                        collected.append(delta)
                        yield delta
                elif event_type == "conversation.item.input_audio_transcription.completed":
                    transcript = (data.get("transcript") or "").strip()
                    if transcript:
                        self._last_input_text = transcript
                elif event_type == "response.done":
                    break
                elif event_type == "response.text.done":
                    break
                elif event_type == "error":
                    if self._is_ignorable_runtime_error(data):
                        continue
                    error_msg = self._extract_error_message(data)
                    raise OmniTransportError(f"omni response error: {error_msg}")
                elif event_type == "_ws_closed":
                    # 如果还没收到任何响应就断开，说明连接有问题
                    if not collected:
                        raise OmniTransportError("omni websocket closed before receiving response")
                    # 如果已经收到部分响应，则正常结束
                    break
            return

        prompt = fallback_prompt
        if not prompt:
            prompt = self._last_input_text
        content = prompt if not context else f"{context}\n\n用户：{prompt}"
        messages = [{"role": "user", "content": content}]
        async for delta in self.provider.chat_stream(messages):
            if delta:
                yield delta

    async def get_last_input_text(self) -> str:
        return self._last_input_text

    async def close(self) -> None:
        if self._reader_task and not self._reader_task.done():
            self._reader_task.cancel()
            try:
                await self._reader_task
            except (Exception, asyncio.CancelledError):
                pass
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
        self._connect_ready = asyncio.Event()
        self._connect_error = ""
