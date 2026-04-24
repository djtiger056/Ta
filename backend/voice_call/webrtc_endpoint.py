"""aiortc WebRTC 端点封装。"""

from __future__ import annotations

import asyncio
from typing import Awaitable, Callable, Optional


class WebRTCEndpoint:
    """服务端 WebRTC 端点（无 aiortc 时安全降级）。"""

    def __init__(
        self,
        on_local_candidate: Callable[[dict], Awaitable[None]],
    ):
        self.on_local_candidate = on_local_candidate
        self.available = False
        self._pc = None
        self._audio_track = None
        self._setup_done = False

    async def setup(self) -> bool:
        if self._setup_done:
            return self.available

        self._setup_done = True
        try:
            from aiortc import RTCPeerConnection
            from aiortc.contrib.media import MediaBlackhole
            from .webrtc_tracks import BotAudioTrack
        except Exception:
            self.available = False
            return False

        self._pc = RTCPeerConnection()
        self._audio_track = BotAudioTrack()
        self._sink = MediaBlackhole()

        @self._pc.on("icecandidate")
        async def _on_icecandidate(candidate):
            if candidate is None:
                return
            payload = {
                "candidate": getattr(candidate, "candidate", ""),
                "sdpMid": getattr(candidate, "sdpMid", None),
                "sdpMLineIndex": getattr(candidate, "sdpMLineIndex", None),
                "usernameFragment": getattr(candidate, "usernameFragment", None),
            }
            await self.on_local_candidate(payload)

        @self._pc.on("track")
        async def _on_track(track):
            if track.kind == "audio":
                self._sink.addTrack(track)

        self.available = True
        return True

    async def handle_offer(self, sdp: str, sdp_type: str = "offer") -> Optional[dict]:
        ok = await self.setup()
        if not ok or self._pc is None:
            return None

        from aiortc import RTCSessionDescription

        await self._pc.setRemoteDescription(RTCSessionDescription(sdp=sdp, type=sdp_type))
        if self._audio_track is not None:
            self._pc.addTrack(self._audio_track.track)
        answer = await self._pc.createAnswer()
        await self._pc.setLocalDescription(answer)
        return {
            "type": self._pc.localDescription.type,
            "sdp": self._pc.localDescription.sdp,
        }

    async def add_ice_candidate(self, candidate_data: dict) -> None:
        if not self.available or self._pc is None:
            return
        from aiortc import RTCIceCandidate

        candidate = RTCIceCandidate(
            sdpMid=candidate_data.get("sdpMid"),
            sdpMLineIndex=candidate_data.get("sdpMLineIndex"),
            candidate=candidate_data.get("candidate", ""),
        )
        await self._pc.addIceCandidate(candidate)

    async def push_audio(self, pcm_data: bytes, sample_rate: int = 16000) -> None:
        if not self.available or self._audio_track is None:
            return
        await self._audio_track.enqueue_pcm(pcm_data, sample_rate=sample_rate)

    async def close(self) -> None:
        if self._pc is not None:
            await self._pc.close()
        self._pc = None
        self._audio_track = None
        self.available = False
