import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest

from backend.voice_call.config import VoiceCallConfig
from backend.voice_call.manager import VoiceCallManager


class _DummyAdapter:
    def __init__(self):
        self.user_id = "ai_user"
        self.calls = []

    async def _request_json(self, method, path, json_data=None, with_token=True):
        self.calls.append((method, path, json_data, with_token))
        return {"ok": True}


@pytest.mark.asyncio
async def test_invite_triggers_accept():
    adapter = _DummyAdapter()
    cfg = VoiceCallConfig(enabled=True, auto_answer=True, answer_delay_seconds=0)
    manager = VoiceCallManager(adapter, cfg)

    await manager.handle_video_signal(
        {
            "type": "invite",
            "callId": "c1",
            "fromId": "u1",
            "audioOnly": True,
        }
    )

    assert any(path == "/v1/api/video/accept" for _, path, _, _ in adapter.calls)


@pytest.mark.asyncio
async def test_hangup_cleans_session():
    adapter = _DummyAdapter()
    cfg = VoiceCallConfig(enabled=True, auto_answer=True, answer_delay_seconds=0)
    manager = VoiceCallManager(adapter, cfg)

    await manager.handle_video_signal({"type": "invite", "callId": "c2", "fromId": "u2", "audioOnly": True})
    assert "c2" in manager.sessions

    await manager.handle_video_signal({"type": "hangup", "callId": "c2", "fromId": "u2"})
    assert "c2" not in manager.sessions

