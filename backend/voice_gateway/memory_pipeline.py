"""语音会话记忆流水线。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Dict, List

from backend.utils.datetime_utils import get_now

from .config import VoiceGatewayMemoryConfig

if TYPE_CHECKING:
    from backend.core.bot import Bot


@dataclass
class _MemoryMessage:
    role: str
    content: str
    timestamp: object


class VoiceMemoryPipeline:
    """实现 start/turn/end 记忆策略。"""

    def __init__(self, bot: "Bot", cfg: VoiceGatewayMemoryConfig):
        self.bot = bot
        self.cfg = cfg
        self._short_window: Dict[str, List[Dict[str, str]]] = {}
        self._compressed: Dict[str, str] = {}
        self._finalized: Dict[str, bool] = {}

    async def _ensure_memory_manager(self):
        manager = getattr(self.bot, "memory_manager", None)
        if manager is None:
            return None
        ok = await self.bot._ensure_memory_manager_initialized()
        if not ok:
            return None
        return manager

    async def on_session_start(self, session_id: str, user_id: str, chat_id: str) -> str:
        manager = await self._ensure_memory_manager()
        if manager is None:
            return ""

        short_memories = await manager.get_short_term_memories(
            user_id=user_id,
            session_id=chat_id,
            limit=max(1, self.cfg.short_term_rounds_n * 2),
        )
        mid_summaries = await manager.get_mid_term_summaries(
            user_id=user_id,
            session_id=chat_id,
            limit=self.cfg.mid_term_rounds_n,
        )

        lines: List[str] = []
        if short_memories:
            lines.append("短期记忆：")
            for item in short_memories[-self.cfg.short_term_rounds_n * 2:]:
                message = item.get("message") or {}
                role = message.get("role", "unknown")
                content = (message.get("content", "") or "").strip()
                if content:
                    lines.append(f"- [{role}] {content}")

        if mid_summaries:
            lines.append("中期记忆摘要：")
            for item in reversed(mid_summaries):
                summary = (item.get("summary") or "").strip()
                if summary:
                    lines.append(f"- {summary}")

        self._short_window[session_id] = []
        self._compressed[session_id] = ""
        self._finalized[session_id] = False

        return "\n".join(lines)

    async def on_turn(
        self,
        session_id: str,
        user_id: str,
        chat_id: str,
        user_text: str,
        ai_text: str,
    ) -> str:
        window = self._short_window.setdefault(session_id, [])
        window.extend([
            {"role": "user", "content": user_text},
            {"role": "assistant", "content": ai_text},
        ])

        max_messages = max(2, self.cfg.short_term_window_rounds * 2)
        if len(window) > max_messages:
            self._short_window[session_id] = window[-max_messages:]
            window = self._short_window[session_id]

        manager = await self._ensure_memory_manager()
        if manager is not None:
            await manager.add_short_term_memory(
                user_id=user_id,
                session_id=chat_id,
                message=_MemoryMessage(role="user", content=user_text, timestamp=get_now()),
            )
            await manager.add_short_term_memory(
                user_id=user_id,
                session_id=chat_id,
                message=_MemoryMessage(role="assistant", content=ai_text, timestamp=get_now()),
            )

        round_count = len(window) // 2
        char_count = sum(len(item.get("content", "")) for item in window)
        if round_count > self.cfg.compress_trigger_rounds or char_count > self.cfg.compress_trigger_chars:
            compressed = await self._compress_window(window)
            self._compressed[session_id] = compressed
            return compressed

        return self._compressed.get(session_id, "")

    async def _compress_window(self, window: List[Dict[str, str]]) -> str:
        if not window:
            return ""
        lines = []
        for item in window:
            role = item.get("role", "unknown")
            content = (item.get("content", "") or "").strip()
            if content:
                lines.append(f"[{role}] {content}")
        merged = "；".join(lines)
        if len(merged) > self.cfg.summary_max_chars:
            return merged[: self.cfg.summary_max_chars] + "..."
        return merged

    async def finalize(
        self,
        session_id: str,
        user_id: str,
        chat_id: str,
        reason: str,
    ) -> bool:
        if self._finalized.get(session_id):
            return True

        manager = await self._ensure_memory_manager()
        if manager is None:
            self._finalized[session_id] = True
            return True

        window = self._short_window.get(session_id, [])
        if not window:
            self._finalized[session_id] = True
            self._short_window.pop(session_id, None)
            self._compressed.pop(session_id, None)
            return True

        processed = False
        if hasattr(manager, "summarize_pending_now"):
            try:
                result = await manager.summarize_pending_now(user_id=user_id, session_id=chat_id, force=True)
                processed = bool((result or {}).get("processed"))
            except Exception:
                processed = False

        if not processed and hasattr(manager, "_generate_conversation_summary"):
            current_round = max(1, len(window) // 2)
            try:
                await manager._generate_conversation_summary(
                    session_id=chat_id,
                    user_id=user_id,
                    current_round=current_round,
                )
            except Exception:
                pass

        self._finalized[session_id] = True
        self._short_window.pop(session_id, None)
        self._compressed.pop(session_id, None)
        return True
