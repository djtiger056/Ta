import asyncio

import pytest
from sqlalchemy import func
from sqlalchemy.future import select

from backend.memory.base import BaseMemoryManager
from backend.memory.models import ConversationMessage, MemoryConfig, MemoryItemDB, MemorySummaryDB
import backend.memory.base as memory_base


class DummyMemoryManager(BaseMemoryManager):
    async def initialize(self):
        await self._init_database()

    async def add_long_term_memory(self, user_id: str, content: str, importance: float = None, metadata=None) -> bool:
        return True

    async def search_long_term_memories(self, user_id: str, query: str, top_k: int = None, score_threshold: float = None):
        return []

    async def get_long_term_memories(self, user_id: str, limit: int = 100):
        return []

    async def _extract_important_memories(self, session_id: str, user_id: str):
        return None

    async def _cleanup_old_long_term_memories(self, user_id: str):
        return None

    async def clear_all_memories(self, user_id: str, session_id: str = None):
        return True


class FakeSummarizer:
    def __init__(self, cfg):
        self.cfg = cfg

    async def summarize_and_extract(self, conversations, overlap_tail=None, max_facts: int = 20):
        return "回归测试摘要", [], {"mocked": True, "source_count": len(conversations)}


def test_manual_force_summary_processes_remaining_pending(tmp_path, monkeypatch):
    async def _run():
        db_file = tmp_path / "memory_force_regression.db"
        db_url = f"sqlite+aiosqlite:///{db_file.as_posix()}"
        cfg = MemoryConfig(
            pipeline_enabled=True,
            short_term_enabled=True,
            short_term_max_rounds=0,
            short_term_keep_rounds=0,
            mid_term_enabled=True,
            long_term_enabled=False,
            pending_enabled=True,
            summarizer_enabled=True,
            pending_chunk_rounds=2,
            summarizer_llm={"provider": "mock", "model": "mock", "api_key": "mock"},
        )
        manager = DummyMemoryManager(cfg, db_url=db_url)
        await manager.initialize()
        monkeypatch.setattr(memory_base, "LLMSummarizer", FakeSummarizer)

        user_id = "u_force"
        session_id = "s_force"
        messages = [
            ConversationMessage(role="user", content="u1"),
            ConversationMessage(role="assistant", content="a1"),
        ]
        await manager.add_short_term_memories_batch(user_id=user_id, session_id=session_id, messages=messages)
        await manager._roll_short_term_to_pending(user_id=user_id, session_id=session_id)

        pending_before = await manager.get_pending_memories(user_id=user_id, session_id=session_id, limit=10)
        assert len(pending_before) == 2

        result = await manager.summarize_pending_now(user_id=user_id, session_id=session_id, force=True)
        assert result["ok"] is True
        assert result["processed"] is True
        assert result["processed_batches"] == 1

        pending_after = await manager.get_pending_memories(user_id=user_id, session_id=session_id, limit=10)
        assert len(pending_after) == 0

        summaries = await manager.get_mid_term_summaries(user_id=user_id, session_id=session_id, limit=10)
        assert len(summaries) == 1
        assert summaries[0]["summary"] == "回归测试摘要"

    asyncio.run(_run())


def test_summary_write_not_blocked_by_json_batch_id_mutation(tmp_path, monkeypatch):
    async def _run():
        db_file = tmp_path / "memory_batch_regression.db"
        db_url = f"sqlite+aiosqlite:///{db_file.as_posix()}"
        cfg = MemoryConfig(
            pipeline_enabled=True,
            short_term_enabled=True,
            short_term_max_rounds=0,
            short_term_keep_rounds=0,
            mid_term_enabled=True,
            long_term_enabled=False,
            pending_enabled=True,
            summarizer_enabled=True,
            pending_chunk_rounds=2,
            summarizer_llm={"provider": "mock", "model": "mock", "api_key": "mock"},
        )
        manager = DummyMemoryManager(cfg, db_url=db_url)
        await manager.initialize()
        monkeypatch.setattr(memory_base, "LLMSummarizer", FakeSummarizer)

        user_id = "u_batch"
        session_id = "s_batch"

        for i in range(4):
            role = "user" if i % 2 == 0 else "assistant"
            await manager.add_short_term_memory(
                user_id=user_id,
                session_id=session_id,
                message=ConversationMessage(role=role, content=f"m{i}"),
            )

        await manager._roll_short_term_to_pending(user_id=user_id, session_id=session_id)

        result = await manager.summarize_pending_now(user_id=user_id, session_id=session_id, force=False)
        assert result["ok"] is True
        assert result["processed"] is True

        async with manager.async_session() as session:
            stmt = select(func.count(MemorySummaryDB.id)).where(
                MemorySummaryDB.user_id == user_id,
                MemorySummaryDB.session_id == session_id,
            )
            count = int((await session.execute(stmt)).scalar() or 0)
            assert count == 1

            pending_processing_stmt = select(func.count(MemoryItemDB.id)).where(
                MemoryItemDB.user_id == user_id,
                MemoryItemDB.session_id == session_id,
                MemoryItemDB.memory_type == "pending_processing",
            )
            pending_processing_count = int((await session.execute(pending_processing_stmt)).scalar() or 0)
            assert pending_processing_count == 0

    asyncio.run(_run())
