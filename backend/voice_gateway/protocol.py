"""语音网关协议定义。"""

from enum import Enum
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class VoiceErrorCode(str, Enum):
    INVALID_TOKEN = "INVALID_TOKEN"
    TOKEN_EXPIRED = "TOKEN_EXPIRED"
    GATEWAY_DISABLED = "GATEWAY_DISABLED"
    SESSION_NOT_FOUND = "SESSION_NOT_FOUND"
    SESSION_CONFLICT = "SESSION_CONFLICT"
    SESSION_NOT_STARTED = "SESSION_NOT_STARTED"
    SESSION_ALREADY_ENDED = "SESSION_ALREADY_ENDED"
    SESSION_TIMEOUT = "SESSION_TIMEOUT"
    SESSION_FAILED = "SESSION_FAILED"
    TOO_MANY_SESSIONS = "TOO_MANY_SESSIONS"
    BAD_EVENT = "BAD_EVENT"
    BAD_AUDIO_FRAME = "BAD_AUDIO_FRAME"
    INTERNAL_ERROR = "INTERNAL_ERROR"


RETRYABLE_ERROR_CODES = {
    VoiceErrorCode.SESSION_TIMEOUT,
    VoiceErrorCode.INTERNAL_ERROR,
    VoiceErrorCode.SESSION_FAILED,
}


class VoiceEventType(str, Enum):
    SESSION_START = "session.start"
    SESSION_STARTED = "session.started"
    SESSION_END = "session.end"
    SESSION_ENDED = "session.ended"
    INTERRUPT = "interrupt"
    PING = "ping"
    PONG = "pong"
    TRANSCRIPT_USER = "transcript.user"
    TRANSCRIPT_AI_DELTA = "transcript.ai.delta"
    TRANSCRIPT_AI_DONE = "transcript.ai.done"
    ERROR = "error"


class BaseEvent(BaseModel):
    event: str
    payload: Dict[str, Any] = Field(default_factory=dict)


class ErrorPayload(BaseModel):
    code: VoiceErrorCode
    message: str
    retryable: bool
    retry_after_ms: Optional[int] = None


class ErrorEvent(BaseModel):
    event: str = VoiceEventType.ERROR.value
    payload: ErrorPayload


class SessionStartPayload(BaseModel):
    user_id: str
    chat_id: str
    device_id: Optional[str] = None
    platform: Optional[str] = None


class SessionStartedPayload(BaseModel):
    session_id: str
    user_id: str
    chat_id: str
    sample_rate: int
    channels: int
    frame_ms: int


class SessionEndPayload(BaseModel):
    reason: Optional[str] = None


class InterruptPayload(BaseModel):
    reason: Optional[str] = None


def is_retryable(code: VoiceErrorCode) -> bool:
    return code in RETRYABLE_ERROR_CODES


def build_error_event(
    code: VoiceErrorCode,
    message: str,
    retry_after_ms: Optional[int] = None,
) -> Dict[str, Any]:
    payload = ErrorPayload(
        code=code,
        message=message,
        retryable=is_retryable(code),
        retry_after_ms=retry_after_ms,
    )
    return ErrorEvent(payload=payload).model_dump(mode="json")


def parse_text_event(raw: Dict[str, Any]) -> BaseEvent:
    event = BaseEvent.model_validate(raw)
    if not event.event:
        raise ValueError("missing event")
    if not isinstance(event.payload, dict):
        raise ValueError("payload must be object")
    return event

