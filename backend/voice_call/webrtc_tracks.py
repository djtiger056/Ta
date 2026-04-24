"""aiortc 音频轨道实现。"""

from __future__ import annotations

import asyncio
import fractions
from typing import Optional


class BotAudioTrack:
    """将 PCM 队列喂给 aiortc 的 AudioStreamTrack。"""

    def __init__(self):
        from aiortc import MediaStreamTrack

        class _Track(MediaStreamTrack):
            kind = "audio"

            def __init__(self, queue: asyncio.Queue):
                super().__init__()
                self._queue = queue
                self._pts = 0

            async def recv(self):
                from av import AudioFrame

                pcm_data, sample_rate = await self._queue.get()
                if not pcm_data:
                    pcm_data = b"\x00" * 640
                    sample_rate = 16000

                samples = len(pcm_data) // 2
                frame = AudioFrame(format="s16", layout="mono", samples=samples)
                frame.sample_rate = sample_rate
                frame.planes[0].update(pcm_data)
                frame.pts = self._pts
                frame.time_base = fractions.Fraction(1, sample_rate)
                self._pts += samples
                return frame

        self._queue: asyncio.Queue = asyncio.Queue(maxsize=200)
        self.track = _Track(self._queue)

    async def enqueue_pcm(self, pcm_data: bytes, sample_rate: int = 16000) -> None:
        if not pcm_data:
            return
        try:
            self._queue.put_nowait((pcm_data, sample_rate))
        except asyncio.QueueFull:
            _ = await self._queue.get()
            await self._queue.put((pcm_data, sample_rate))

