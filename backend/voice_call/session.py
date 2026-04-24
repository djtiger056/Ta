"""通话会话状态机。"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from backend.utils.datetime_utils import get_now


class CallState(str, Enum):
    IDLE = "IDLE"
    INCOMING_RINGING = "INCOMING_RINGING"
    CONNECTING = "CONNECTING"
    CONNECTED = "CONNECTED"
    ENDED = "ENDED"
    FAILED = "FAILED"


@dataclass
class CallSession:
    call_id: str
    peer_user_id: str
    is_audio_only: bool = True
    state: CallState = CallState.IDLE
    created_at: object = field(default_factory=get_now)
    started_at: Optional[object] = None
    ended_at: Optional[object] = None

    def set_state(self, state: CallState) -> None:
        self.state = state
        if state == CallState.CONNECTED and self.started_at is None:
            self.started_at = get_now()
        if state in {CallState.ENDED, CallState.FAILED}:
            self.ended_at = get_now()

