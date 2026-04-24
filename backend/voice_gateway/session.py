"""语音会话状态机与会话对象。"""

import asyncio
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from backend.utils.datetime_utils import get_now


class VoiceSessionState(str, Enum):
    INIT = "INIT"
    AUTHED = "AUTHED"
    STARTED = "STARTED"
    ACTIVE = "ACTIVE"
    ENDING = "ENDING"
    ENDED = "ENDED"
    FAILED = "FAILED"
    TIMEOUT = "TIMEOUT"


@dataclass
class VoiceSession:
    session_id: str
    user_id: str
    chat_id: str
    device_id: str
    platform: str
    state: VoiceSessionState = VoiceSessionState.INIT
    created_at: object = field(default_factory=get_now)
    last_active_at: object = field(default_factory=get_now)
    started_at: Optional[object] = None
    ended_at: Optional[object] = None
    finalized: bool = False
    is_cancel_requested: bool = False
    active_response_task: Optional[asyncio.Task] = None

    def transit(self, new_state: VoiceSessionState) -> None:
        self.state = new_state
        self.last_active_at = get_now()
        if new_state in {VoiceSessionState.STARTED, VoiceSessionState.ACTIVE} and self.started_at is None:
            self.started_at = get_now()
        if new_state in {VoiceSessionState.ENDED, VoiceSessionState.FAILED, VoiceSessionState.TIMEOUT}:
            self.ended_at = get_now()

    def touch(self) -> None:
        self.last_active_at = get_now()

    @property
    def is_terminal(self) -> bool:
        return self.state in {
            VoiceSessionState.ENDED,
            VoiceSessionState.FAILED,
            VoiceSessionState.TIMEOUT,
        }

