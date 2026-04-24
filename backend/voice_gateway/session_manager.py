"""语音会话管理器。"""

import asyncio
import uuid
from datetime import timedelta
from typing import Dict, List, Optional

from backend.utils.datetime_utils import get_now

from .config import VoiceGatewayConfig
from .session import VoiceSession, VoiceSessionState


class VoiceSessionManager:
    """维护会话表、并发控制与超时清理。"""

    def __init__(self, cfg: VoiceGatewayConfig):
        self.cfg = cfg
        self._sessions: Dict[str, VoiceSession] = {}
        self._lock = asyncio.Lock()

    async def create_session(
        self,
        user_id: str,
        chat_id: str,
        device_id: str,
        platform: str,
    ) -> VoiceSession:
        async with self._lock:
            if len(self._sessions) >= self.cfg.call.max_concurrent_sessions:
                raise RuntimeError("too many sessions")

            session_id = uuid.uuid4().hex
            session = VoiceSession(
                session_id=session_id,
                user_id=user_id,
                chat_id=chat_id,
                device_id=device_id,
                platform=platform,
            )
            session.transit(VoiceSessionState.AUTHED)
            self._sessions[session_id] = session
            return session

    async def get_session(self, session_id: str) -> Optional[VoiceSession]:
        async with self._lock:
            return self._sessions.get(session_id)

    async def remove_session(self, session_id: str) -> None:
        async with self._lock:
            self._sessions.pop(session_id, None)

    async def mark_timeout_if_needed(self, session: VoiceSession) -> bool:
        now = get_now()
        if session.started_at is not None:
            if now - session.started_at >= timedelta(seconds=self.cfg.call.max_duration_seconds):
                session.transit(VoiceSessionState.TIMEOUT)
                return True

        if now - session.last_active_at >= timedelta(seconds=self.cfg.call.idle_timeout_seconds):
            session.transit(VoiceSessionState.TIMEOUT)
            return True

        return False

    async def cleanup_timed_out(self) -> List[VoiceSession]:
        timed_out: List[VoiceSession] = []
        async with self._lock:
            now = get_now()
            to_remove: List[str] = []

            for session_id, session in self._sessions.items():
                expired = False
                if session.started_at is not None and now - session.started_at >= timedelta(seconds=self.cfg.call.max_duration_seconds):
                    expired = True
                if now - session.last_active_at >= timedelta(seconds=self.cfg.call.idle_timeout_seconds):
                    expired = True

                if expired:
                    session.transit(VoiceSessionState.TIMEOUT)
                    timed_out.append(session)
                    to_remove.append(session_id)

            for session_id in to_remove:
                self._sessions.pop(session_id, None)

        return timed_out

    async def count(self) -> int:
        async with self._lock:
            return len(self._sessions)

