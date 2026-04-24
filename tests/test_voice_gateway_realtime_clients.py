import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import asyncio

import pytest

from backend.voice_gateway.config import VoiceGatewayConfig
from backend.voice_gateway.omni_client import OmniClient


@pytest.mark.asyncio
async def test_omni_stream_response_from_queue():
    cfg = VoiceGatewayConfig.model_validate({"enabled": True})
    client = OmniClient(cfg.omni)

    await client._queue.put({"type": "response.text.delta", "delta": "你"})
    await client._queue.put({"type": "response.text.delta", "delta": "好"})
    await client._queue.put({"type": "response.done"})

    client._ws = object()
    chunks = []
    async for delta in client.stream_response(fallback_prompt="", context=""):
        chunks.append(delta)

    assert "".join(chunks) == "你好"


@pytest.mark.asyncio
async def test_omni_transcript_event_updates_last_input():
    cfg = VoiceGatewayConfig.model_validate({"enabled": True})
    client = OmniClient(cfg.omni)

    await client._queue.put({"type": "conversation.item.input_audio_transcription.completed", "transcript": "测试输入"})
    await client._queue.put({"type": "response.done"})

    client._ws = object()
    async for _ in client.stream_response(fallback_prompt="", context=""):
        pass

    assert await client.get_last_input_text() == "测试输入"

