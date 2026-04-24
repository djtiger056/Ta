"""AI 实时语音会话网关 API。"""

from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Request, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field

from backend.config import config
from backend.core.bot import Bot

from backend.voice_gateway.audio_pipeline import AudioPipeline
from backend.voice_gateway.auth import VoiceTokenError, VoiceTokenManager
from backend.voice_gateway.config import VoiceGatewayConfig
from backend.voice_gateway.memory_pipeline import VoiceMemoryPipeline
from backend.voice_gateway.metrics import VoiceGatewayMetrics
from backend.voice_gateway.omni_client import OmniClient, OmniTransportError
from backend.voice_gateway.protocol import (
    VoiceErrorCode,
    VoiceEventType,
    build_error_event,
    parse_text_event,
)
from backend.voice_gateway.session import VoiceSession, VoiceSessionState
from backend.voice_gateway.session_manager import VoiceSessionManager
from backend.voice_gateway.tts_client import TTSClient


logger = logging.getLogger(__name__)
router = APIRouter(tags=["voice-session"])


class VoiceSessionTokenRequest(BaseModel):
    chat_id: str = Field(min_length=1)
    user_id: str = Field(min_length=1)
    device_id: str = Field(default="")
    platform: str = Field(default="")


class VoiceSessionTokenResponse(BaseModel):
    token: str
    expires_in: int
    session_id: str
    ws_url: str


@dataclass
class VoiceGatewayRuntime:
    cfg: VoiceGatewayConfig
    manager: VoiceSessionManager
    token_manager: VoiceTokenManager
    bot: Bot
    metrics: VoiceGatewayMetrics


_runtime: Optional[VoiceGatewayRuntime] = None


def _build_runtime(force_reload: bool = False) -> VoiceGatewayRuntime:
    global _runtime
    if _runtime is not None and not force_reload:
        return _runtime

    cfg = config.voice_gateway_config
    runtime = VoiceGatewayRuntime(
        cfg=cfg,
        manager=VoiceSessionManager(cfg),
        token_manager=VoiceTokenManager(cfg.auth),
        bot=Bot(),
        metrics=VoiceGatewayMetrics(),
    )
    _runtime = runtime
    return runtime


async def _send_error(
    websocket: WebSocket,
    code: VoiceErrorCode,
    message: str,
    retry_after_ms: Optional[int] = None,
) -> bool:
    return await _safe_send_json(websocket, build_error_event(code, message, retry_after_ms))


async def _safe_send_json(websocket: WebSocket, payload: Dict[str, Any]) -> bool:
    try:
        await websocket.send_json(payload)
        return True
    except Exception as exc:
        logger.debug("skip ws json send on closed/closing connection: %s", exc)
        return False


async def _safe_send_bytes(websocket: WebSocket, payload: bytes) -> bool:
    try:
        await websocket.send_bytes(payload)
        return True
    except Exception as exc:
        logger.debug("skip ws bytes send on closed/closing connection: %s", exc)
        return False


def _build_ws_url(request: Request, ws_path: str, token: str) -> str:
    forwarded_proto = (request.headers.get("x-forwarded-proto") or "").split(",")[0].strip().lower()
    forwarded_host = (request.headers.get("x-forwarded-host") or "").split(",")[0].strip()
    host = forwarded_host or request.headers.get("host") or request.url.netloc
    scheme = "wss" if (forwarded_proto == "https" or request.url.scheme == "https") else "ws"
    return f"{scheme}://{host}{ws_path}?token={token}"


@router.post("/api/voice-session/token", response_model=VoiceSessionTokenResponse)
async def create_voice_session_token(payload: VoiceSessionTokenRequest, request: Request):
    runtime = _build_runtime()
    logger.info(
        "voice token request: user_id=%s chat_id=%s device_id=%s platform=%s",
        payload.user_id,
        payload.chat_id,
        payload.device_id,
        payload.platform,
    )
    if not runtime.cfg.enabled:
        raise HTTPException(status_code=503, detail="voice gateway disabled")

    try:
        session = await runtime.manager.create_session(
            user_id=payload.user_id,
            chat_id=payload.chat_id,
            device_id=payload.device_id,
            platform=payload.platform,
        )
    except RuntimeError:
        raise HTTPException(status_code=429, detail="too many sessions")

    token = runtime.token_manager.create_token(
        session_id=session.session_id,
        user_id=payload.user_id,
        chat_id=payload.chat_id,
        device_id=payload.device_id,
        platform=payload.platform,
    )

    runtime.metrics.inc("token_issued")
    ws_url = _build_ws_url(request, runtime.cfg.ws.path, token)
    return VoiceSessionTokenResponse(
        token=token,
        expires_in=runtime.cfg.auth.token_ttl_seconds,
        session_id=session.session_id,
        ws_url=ws_url,
    )


@router.post("/api/voice-session/reload")
async def reload_voice_gateway():
    config.refresh_from_file()
    _build_runtime(force_reload=True)
    return {"ok": True}


async def _interrupt_current_response(
    session: VoiceSession,
    pipeline: AudioPipeline,
    tts_client: TTSClient,
) -> None:
    session.is_cancel_requested = True
    task = session.active_response_task
    if task and not task.done():
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        except Exception:
            pass
    session.active_response_task = None

    await tts_client.clear()
    pipeline.clear_downstream()
    pipeline.reset_interrupt_state()


async def _handle_turn(
    websocket: WebSocket,
    runtime: VoiceGatewayRuntime,
    session: VoiceSession,
    memory_pipeline: VoiceMemoryPipeline,
    omni_client: OmniClient,
    tts_client: TTSClient,
    pipeline: AudioPipeline,
    audio_payload: bytes,
    fallback_context: str,
) -> None:
    # 将整个交互流程包装在一个函数中，以便重试
    async def _execute_turn() -> tuple[str, str]:
        """执行一次完整的交互：发送音频 + 接收响应。返回 (user_text, ai_text)"""
        await omni_client.send_audio(audio_payload)
        await omni_client.commit_audio()

        context = fallback_context
        ai_chunks = []
        async for delta in omni_client.stream_response(fallback_prompt="", context=context):
            ai_chunks.append(delta)
            sent = await _safe_send_json(websocket, {
                "event": VoiceEventType.TRANSCRIPT_AI_DELTA.value,
                "payload": {"delta": delta},
            })
            if not sent:
                return "", ""

        user_text = (await omni_client.get_last_input_text() or "").strip()
        ai_text = "".join(ai_chunks).strip()
        return user_text, ai_text

    # 尝试执行交互，如果失败则重连重试
    max_retries = 2
    user_text = ""
    ai_text = ""
    last_omni_error: Optional[OmniTransportError] = None

    if not omni_client.is_connected:
        reconnected = await omni_client.connect(instructions=fallback_context)
        if not reconnected:
            raise OmniTransportError("omni websocket not connected at turn start")

    for attempt in range(max_retries):
        try:
            user_text, ai_text = await _execute_turn()
            last_omni_error = None
            break  # 成功则跳出循环
        except OmniTransportError as e:
            last_omni_error = e
            if attempt < max_retries - 1:
                logger.warning(f"Omni transport error on attempt {attempt + 1}, reconnecting: {e}")
                await omni_client.close()
                reconnected = await omni_client.connect(instructions=fallback_context)
                if not reconnected:
                    logger.error("Failed to reconnect to omni service")
                    break
            else:
                logger.error(f"Failed to complete turn after {max_retries} attempts")

    if last_omni_error is not None and not (user_text or ai_text):
        raise last_omni_error

    # 发送转录结果给客户端
    if user_text:
        if not await _safe_send_json(websocket, {
            "event": VoiceEventType.TRANSCRIPT_USER.value,
            "payload": {"text": user_text},
        }):
            return

    if not await _safe_send_json(websocket, {
        "event": VoiceEventType.TRANSCRIPT_AI_DONE.value,
        "payload": {"text": ai_text},
    }):
        return

    # 更新记忆
    if user_text or ai_text:
        compressed = await memory_pipeline.on_turn(
            session_id=session.session_id,
            user_id=session.user_id,
            chat_id=session.chat_id,
            user_text=user_text,
            ai_text=ai_text,
        )
    else:
        runtime.metrics.inc("turn_empty_text")

    # TTS 合成并发送音频
    if runtime.cfg.tts.enabled and ai_text:
        async for frame in tts_client.synthesize_stream(ai_text, user_id=session.user_id, frame_bytes=pipeline.frame_bytes):
            pipeline.append_downstream(frame)

        for chunk in pipeline.pop_all_downstream():
            if not await _safe_send_bytes(websocket, chunk):
                return


async def _finalize_session(
    runtime: VoiceGatewayRuntime,
    websocket: WebSocket,
    session: VoiceSession,
    memory_pipeline: VoiceMemoryPipeline,
    reason: str,
) -> None:
    if session.state not in {VoiceSessionState.TIMEOUT, VoiceSessionState.FAILED}:
        session.transit(VoiceSessionState.ENDING)

    await memory_pipeline.finalize(
        session_id=session.session_id,
        user_id=session.user_id,
        chat_id=session.chat_id,
        reason=reason,
    )

    if session.state not in {VoiceSessionState.TIMEOUT, VoiceSessionState.FAILED}:
        session.transit(VoiceSessionState.ENDED)

    try:
        await websocket.send_json({
            "event": VoiceEventType.SESSION_ENDED.value,
            "payload": {
                "session_id": session.session_id,
                "reason": reason,
                "state": session.state.value,
            },
        })
    except Exception:
        pass

    await runtime.manager.remove_session(session.session_id)


@router.websocket("/ws/voice-session")
async def voice_session_ws(websocket: WebSocket):
    runtime = _build_runtime()
    await websocket.accept()
    logger.info("voice ws accepted: client=%s", websocket.client)

    if not runtime.cfg.enabled:
        await _send_error(websocket, VoiceErrorCode.GATEWAY_DISABLED, "voice gateway disabled")
        await websocket.close(code=1008)
        return

    token = websocket.query_params.get("token", "")
    if not token:
        await _send_error(websocket, VoiceErrorCode.INVALID_TOKEN, "missing token")
        await websocket.close(code=1008)
        return

    try:
        claims = runtime.token_manager.decode_token(token)
    except VoiceTokenError as exc:
        message = str(exc)
        if "expired" in message:
            await _send_error(websocket, VoiceErrorCode.TOKEN_EXPIRED, message)
        else:
            await _send_error(websocket, VoiceErrorCode.INVALID_TOKEN, message)
        await websocket.close(code=1008)
        return

    session_id = str(claims.get("session_id") or "")
    logger.info("voice ws token decoded: session_id=%s", session_id)
    session = await runtime.manager.get_session(session_id)
    if not session:
        await _send_error(websocket, VoiceErrorCode.SESSION_NOT_FOUND, "session not found")
        await websocket.close(code=1008)
        return

    if session.state not in {VoiceSessionState.AUTHED, VoiceSessionState.STARTED, VoiceSessionState.ACTIVE}:
        await _send_error(websocket, VoiceErrorCode.SESSION_CONFLICT, "session state invalid")
        await websocket.close(code=1008)
        return

    runtime.metrics.inc("ws_connected")
    pipeline = AudioPipeline(runtime.cfg.audio)
    omni_client = OmniClient(runtime.cfg.omni)
    tts_client = TTSClient(runtime.bot, runtime.cfg)
    memory_pipeline = VoiceMemoryPipeline(runtime.bot, runtime.cfg.memory)
    audio_buffer = bytearray()
    start_context = ""
    omni_connected = False
    tts_connected = False
    consecutive_upstream_failures = 0

    async def _consume_active_turn_result() -> bool:
        """回收后台 turn 任务结果。返回 True 表示需要中断主循环。"""
        nonlocal consecutive_upstream_failures
        task = session.active_response_task
        if task is None or not task.done():
            return False
        try:
            await task
            runtime.metrics.inc("turn_success")
            consecutive_upstream_failures = 0
        except asyncio.CancelledError:
            runtime.metrics.inc("turn_cancelled")
        except OmniTransportError as exc:
            runtime.metrics.inc("turn_upstream_failed")
            logger.warning("voice turn upstream failed: %s", exc)
            await _send_error(
                websocket,
                VoiceErrorCode.SESSION_FAILED,
                "upstream realtime disconnected",
                retry_after_ms=800,
            )
            consecutive_upstream_failures += 1
            if consecutive_upstream_failures >= 3:
                session.transit(VoiceSessionState.FAILED)
                return True
        except Exception as exc:
            runtime.metrics.inc("turn_failed")
            logger.exception("voice turn failed: %s", exc)
            await _send_error(websocket, VoiceErrorCode.INTERNAL_ERROR, "turn processing failed")
        finally:
            if session.active_response_task is task:
                session.active_response_task = None
        return False

    try:
        while True:
            if await _consume_active_turn_result():
                break

            if await runtime.manager.mark_timeout_if_needed(session):
                runtime.metrics.inc("session_timeout")
                await _send_error(websocket, VoiceErrorCode.SESSION_TIMEOUT, "session timeout", retry_after_ms=1000)
                break

            try:
                message = await asyncio.wait_for(websocket.receive(), timeout=1.0)
            except asyncio.TimeoutError:
                continue

            message_type = message.get("type")
            if message_type == "websocket.disconnect":
                runtime.metrics.inc("ws_disconnected")
                break

            if message_type != "websocket.receive":
                continue

            session.touch()

            if "text" in message and message["text"] is not None:
                raw_text = message["text"]
                try:
                    raw_event = json.loads(raw_text)
                    event = parse_text_event(raw_event)
                except Exception:
                    runtime.metrics.inc("bad_event")
                    await _send_error(websocket, VoiceErrorCode.BAD_EVENT, "invalid text event")
                    continue

                if event.event == VoiceEventType.PING.value:
                    if not await _safe_send_json(websocket, {"event": VoiceEventType.PONG.value, "payload": {}}):
                        break
                    continue

                if event.event == VoiceEventType.SESSION_START.value:
                    if session.state not in {VoiceSessionState.AUTHED, VoiceSessionState.STARTED}:
                        await _send_error(websocket, VoiceErrorCode.SESSION_CONFLICT, "session cannot start")
                        continue

                    start_context = await memory_pipeline.on_session_start(
                        session_id=session.session_id,
                        user_id=session.user_id,
                        chat_id=session.chat_id,
                    )

                    logger.info("Connecting to omni service...")
                    if not omni_connected:
                        omni_connected = await omni_client.connect(instructions=start_context)
                        logger.info(f"Omni connection result: {omni_connected}")
                    if not omni_connected:
                        runtime.metrics.inc("session_start_failed_upstream")
                        await _send_error(
                            websocket,
                            VoiceErrorCode.SESSION_FAILED,
                            "omni realtime unavailable",
                            retry_after_ms=1500,
                        )
                        session.transit(VoiceSessionState.FAILED)
                        break

                    if runtime.cfg.tts.enabled and not tts_connected:
                        logger.info("Connecting to TTS service...")
                        tts_connected = await tts_client.connect()
                        logger.info(f"TTS connection result: {tts_connected}")
                        if not tts_connected:
                            runtime.metrics.inc("session_start_failed_tts")
                            await _send_error(
                                websocket,
                                VoiceErrorCode.SESSION_FAILED,
                                "tts realtime unavailable",
                                retry_after_ms=1500,
                            )
                            session.transit(VoiceSessionState.FAILED)
                            break

                    session.transit(VoiceSessionState.STARTED)
                    session.transit(VoiceSessionState.ACTIVE)
                    runtime.metrics.inc("session_started")
                    logger.info(
                        "voice session started: session_id=%s user_id=%s chat_id=%s omni=%s tts=%s",
                        session.session_id,
                        session.user_id,
                        session.chat_id,
                        omni_connected,
                        tts_connected,
                    )

                    if not await _safe_send_json(websocket, {
                        "event": VoiceEventType.SESSION_STARTED.value,
                        "payload": {
                            "session_id": session.session_id,
                            "user_id": session.user_id,
                            "chat_id": session.chat_id,
                            "sample_rate": runtime.cfg.audio.output_sample_rate,
                            "channels": runtime.cfg.audio.channels,
                            "frame_ms": runtime.cfg.audio.frame_ms,
                            "context_chars": len(start_context),
                        },
                    }):
                        break
                    logger.info("Sent session.started response to client")
                    continue

                if event.event == VoiceEventType.INTERRUPT.value:
                    had_active_response = bool(session.active_response_task and not session.active_response_task.done())
                    await _interrupt_current_response(session, pipeline, tts_client)
                    if had_active_response:
                        await omni_client.cancel_response()
                    runtime.metrics.inc("interrupt")
                    continue

                if event.event == VoiceEventType.SESSION_END.value:
                    runtime.metrics.inc("session_end_event")
                    break

                await _send_error(websocket, VoiceErrorCode.BAD_EVENT, f"unsupported event: {event.event}")
                continue

            if "bytes" in message and message["bytes"] is not None:
                raw_bytes = message["bytes"]
                if session.state not in {VoiceSessionState.STARTED, VoiceSessionState.ACTIVE}:
                    runtime.metrics.inc("audio_before_start")
                    await _send_error(websocket, VoiceErrorCode.SESSION_NOT_STARTED, "session.start required before audio")
                    continue

                if not isinstance(raw_bytes, (bytes, bytearray)):
                    runtime.metrics.inc("bad_audio_frame")
                    await _send_error(websocket, VoiceErrorCode.BAD_AUDIO_FRAME, "audio frame must be bytes")
                    continue

                has_active_response = bool(session.active_response_task and not session.active_response_task.done())
                if not has_active_response:
                    pipeline.reset_interrupt_state()

                if has_active_response and pipeline.should_interrupt_on_frame(bytes(raw_bytes)):
                    await _interrupt_current_response(session, pipeline, tts_client)
                    await omni_client.cancel_response()
                    runtime.metrics.inc("interrupt_by_speech")

                audio_buffer.extend(raw_bytes)
                runtime.metrics.inc("audio_frame_in")

                if len(audio_buffer) >= runtime.cfg.audio.min_turn_bytes:
                    if session.active_response_task and not session.active_response_task.done():
                        # 正在播报/生成时不启动新 turn，继续接收音频用于后续打断后处理。
                        continue

                    chunk = bytes(audio_buffer)
                    audio_buffer.clear()
                    if not any(chunk):
                        runtime.metrics.inc("audio_chunk_all_zero_skipped")
                        continue
                    if not pipeline.detect_speech(chunk):
                        runtime.metrics.inc("audio_chunk_no_speech_skipped")
                        continue
                    session.is_cancel_requested = False

                    async def _run_turn():
                        await _handle_turn(
                            websocket=websocket,
                            runtime=runtime,
                            session=session,
                            memory_pipeline=memory_pipeline,
                            omni_client=omni_client,
                            tts_client=tts_client,
                            pipeline=pipeline,
                            audio_payload=chunk,
                            fallback_context=start_context,
                        )

                    session.active_response_task = asyncio.create_task(_run_turn())
                    continue

    except WebSocketDisconnect:
        runtime.metrics.inc("ws_disconnected")
    except Exception as exc:
        runtime.metrics.inc("ws_failed")
        logger.exception("voice websocket failed: %s", exc)
        session.transit(VoiceSessionState.FAILED)
        try:
            await _send_error(websocket, VoiceErrorCode.INTERNAL_ERROR, "websocket internal error")
        except Exception:
            pass
    finally:
        task = session.active_response_task
        if task is not None:
            if not task.done():
                task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
            except Exception:
                pass
            session.active_response_task = None

        await omni_client.close()
        await tts_client.close()

        reason = "disconnect"
        if session.state == VoiceSessionState.TIMEOUT:
            reason = "timeout"
        elif session.state == VoiceSessionState.FAILED:
            reason = "failed"

        await _finalize_session(
            runtime=runtime,
            websocket=websocket,
            session=session,
            memory_pipeline=memory_pipeline,
            reason=reason,
        )
