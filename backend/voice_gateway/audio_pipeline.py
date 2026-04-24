"""Audio processing helpers for voice gateway."""

from __future__ import annotations

import audioop
import time
from collections import deque
from typing import Deque, List

from .config import VoiceGatewayAudioConfig


class AudioPipeline:
    """Maintains downstream queue and lightweight speech gate state."""

    def __init__(self, cfg: VoiceGatewayAudioConfig):
        self.cfg = cfg
        self._downstream: Deque[bytes] = deque()
        self._recent_rms: Deque[int] = deque(maxlen=max(1, cfg.dynamic_noise_window_frames))
        self._interrupt_speech_streak = 0
        self._last_interrupt_ts = 0.0

    @property
    def frame_bytes(self) -> int:
        samples = int(self.cfg.output_sample_rate * self.cfg.frame_ms / 1000)
        return samples * self.cfg.channels * 2

    @property
    def input_frame_bytes(self) -> int:
        samples = int(self.cfg.input_sample_rate * self.cfg.frame_ms / 1000)
        return samples * self.cfg.channels * 2

    def append_downstream(self, chunk: bytes) -> None:
        if chunk:
            self._downstream.append(chunk)

    def pop_all_downstream(self) -> List[bytes]:
        chunks: List[bytes] = []
        while self._downstream:
            chunks.append(self._downstream.popleft())
        return chunks

    def clear_downstream(self) -> None:
        self._downstream.clear()

    def reset_interrupt_state(self) -> None:
        self._interrupt_speech_streak = 0

    def _compute_rms(self, pcm_chunk: bytes) -> int:
        if not pcm_chunk:
            return 0
        try:
            return max(0, int(audioop.rms(pcm_chunk, 2)))
        except Exception:
            return 0

    def _remember_rms(self, rms: int) -> None:
        if rms > 0:
            self._recent_rms.append(rms)

    def _noise_floor(self) -> int:
        if not self._recent_rms:
            return 0
        ordered = sorted(self._recent_rms)
        percentile = min(max(float(self.cfg.dynamic_noise_percentile), 0.0), 1.0)
        index = int((len(ordered) - 1) * percentile)
        return int(ordered[index])

    def _speech_threshold(self, *, multiplier: float = 1.0) -> int:
        static_threshold = max(1, int(self.cfg.speech_rms_threshold))
        dynamic_threshold = int(self._noise_floor() * self.cfg.dynamic_noise_multiplier + self.cfg.dynamic_noise_margin)
        return int(max(static_threshold, dynamic_threshold) * max(1.0, float(multiplier)))

    def detect_speech(self, pcm_chunk: bytes) -> bool:
        if not pcm_chunk:
            return False

        frame_bytes = max(2, self.input_frame_bytes)
        speech_frames = 0
        min_speech_frames = max(1, int(self.cfg.turn_min_speech_frames))

        for offset in range(0, len(pcm_chunk), frame_bytes):
            frame = pcm_chunk[offset: offset + frame_bytes]
            if len(frame) < 2:
                continue
            rms = self._compute_rms(frame)
            if rms <= 0:
                continue
            self._remember_rms(rms)
            if rms >= self._speech_threshold():
                speech_frames += 1
                if speech_frames >= min_speech_frames:
                    return True

        return False

    def should_interrupt_on_frame(self, pcm_chunk: bytes) -> bool:
        rms = self._compute_rms(pcm_chunk)
        if rms <= 0:
            self._interrupt_speech_streak = 0
            return False

        self._remember_rms(rms)
        threshold = self._speech_threshold(multiplier=self.cfg.interrupt_threshold_multiplier)
        if rms < threshold:
            self._interrupt_speech_streak = 0
            return False

        self._interrupt_speech_streak += 1
        if self._interrupt_speech_streak < max(1, int(self.cfg.interrupt_min_speech_frames)):
            return False

        now = time.monotonic()
        cooldown_ms = max(0, int(self.cfg.interrupt_cooldown_ms))
        if (now - self._last_interrupt_ts) * 1000 < cooldown_ms:
            return False

        self._last_interrupt_ts = now
        self._interrupt_speech_streak = 0
        return True
