import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest

from backend.voice_gateway.config import VoiceGatewayMemoryConfig
from backend.voice_gateway.memory_pipeline import VoiceMemoryPipeline


class _DummySession:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    def add(self, _):
        return None

    async def commit(self):
        return None


class _DummyMemoryManager:
    def __init__(self):
        self.async_session = lambda: _DummySession()

    async def get_short_term_memories(self, **kwargs):
        return [{"message": {"role": "user", "content": "你好"}}]

    async def get_mid_term_summaries(self, **kwargs):
        return [{"summary": "上次聊了出行安排"}]

    async def add_short_term_memory(self, **kwargs):
        return True


class _DummyBot:
    def __init__(self):
        self.memory_manager = _DummyMemoryManager()

    async def _ensure_memory_manager_initialized(self):
        return True


@pytest.mark.asyncio
async def test_memory_pipeline_finalize_idempotent():
    pipeline = VoiceMemoryPipeline(_DummyBot(), VoiceGatewayMemoryConfig())
    context = await pipeline.on_session_start("s1", "u1", "c1")
    assert "短期记忆" in context

    compressed = await pipeline.on_turn("s1", "u1", "c1", "你好吗", "我很好")
    assert isinstance(compressed, str)

    ok1 = await pipeline.finalize("s1", "u1", "c1", "disconnect")
    ok2 = await pipeline.finalize("s1", "u1", "c1", "disconnect")
    assert ok1 is True
    assert ok2 is True

