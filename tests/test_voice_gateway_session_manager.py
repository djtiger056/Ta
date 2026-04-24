import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import asyncio

import pytest

from backend.voice_gateway.config import VoiceGatewayConfig
from backend.voice_gateway.session import VoiceSessionState
from backend.voice_gateway.session_manager import VoiceSessionManager


@pytest.mark.asyncio
async def test_create_and_remove_session():
    cfg = VoiceGatewayConfig.model_validate({"enabled": True})
    manager = VoiceSessionManager(cfg)

    session = await manager.create_session("u1", "c1", "d1", "web")
    assert session.state == VoiceSessionState.AUTHED

    loaded = await manager.get_session(session.session_id)
    assert loaded is not None

    await manager.remove_session(session.session_id)
    loaded2 = await manager.get_session(session.session_id)
    assert loaded2 is None


@pytest.mark.asyncio
async def test_concurrency_limit():
    cfg = VoiceGatewayConfig.model_validate({
        "enabled": True,
        "call": {"max_concurrent_sessions": 1},
    })
    manager = VoiceSessionManager(cfg)

    _ = await manager.create_session("u1", "c1", "d1", "web")
    with pytest.raises(RuntimeError):
        await manager.create_session("u2", "c2", "d2", "web")

