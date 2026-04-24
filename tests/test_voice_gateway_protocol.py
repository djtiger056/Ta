import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.voice_gateway.protocol import (
    BaseEvent,
    VoiceErrorCode,
    build_error_event,
    is_retryable,
    parse_text_event,
)


def test_build_error_event_shape():
    data = build_error_event(VoiceErrorCode.INTERNAL_ERROR, "x", retry_after_ms=100)
    assert data["event"] == "error"
    assert data["payload"]["code"] == VoiceErrorCode.INTERNAL_ERROR.value
    assert data["payload"]["retryable"] is True
    assert data["payload"]["retry_after_ms"] == 100


def test_is_retryable():
    assert is_retryable(VoiceErrorCode.INTERNAL_ERROR) is True
    assert is_retryable(VoiceErrorCode.BAD_EVENT) is False


def test_parse_text_event_ok():
    event = parse_text_event({"event": "ping", "payload": {}})
    assert isinstance(event, BaseEvent)
    assert event.event == "ping"

