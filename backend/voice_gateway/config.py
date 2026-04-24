"""Voice gateway configuration models."""

from typing import Any, Dict

from pydantic import BaseModel, Field


class VoiceGatewayWSConfig(BaseModel):
    path: str = Field(default="/ws/voice-session", description="Voice session websocket path")


class VoiceGatewayAuthConfig(BaseModel):
    token_ttl_seconds: int = Field(default=600, description="Short-lived token ttl in seconds")
    issuer: str = Field(default="lfbot-voice-gateway", description="Token issuer")


class VoiceGatewayCallConfig(BaseModel):
    max_duration_seconds: int = Field(default=1800, description="Max call duration in seconds")
    idle_timeout_seconds: int = Field(default=20, description="Idle timeout in seconds")
    max_concurrent_sessions: int = Field(default=100, description="Max concurrent sessions")


class VoiceGatewayAudioConfig(BaseModel):
    input_sample_rate: int = Field(default=16000, description="Upstream sample rate")
    output_sample_rate: int = Field(default=16000, description="Downstream sample rate")
    channels: int = Field(default=1, description="Audio channels")
    frame_ms: int = Field(default=20, description="Frame duration in milliseconds")
    speech_rms_threshold: int = Field(default=500, description="Static RMS threshold for speech gate")
    min_turn_bytes: int = Field(default=32000, description="Minimum buffered bytes to trigger a turn")
    dynamic_noise_window_frames: int = Field(default=50, description="History window size for dynamic noise floor")
    dynamic_noise_percentile: float = Field(default=0.6, description="Percentile in [0,1] used for dynamic noise floor")
    dynamic_noise_multiplier: float = Field(default=1.8, description="Dynamic threshold multiplier over noise floor")
    dynamic_noise_margin: int = Field(default=120, description="Extra RMS margin added to dynamic threshold")
    turn_min_speech_frames: int = Field(default=2, description="Minimum speech frames required to start a turn")
    interrupt_min_speech_frames: int = Field(default=3, description="Minimum consecutive speech frames required to interrupt")
    interrupt_cooldown_ms: int = Field(default=800, description="Interrupt cooldown in milliseconds")
    interrupt_threshold_multiplier: float = Field(default=1.15, description="Extra strict multiplier for interrupt threshold")


class VoiceGatewayMemoryConfig(BaseModel):
    mid_term_rounds_n: int = Field(default=4, description="Injected mid-term memory rounds at session start")
    short_term_rounds_n: int = Field(default=6, description="Injected short-term memory rounds at session start")
    short_term_window_rounds: int = Field(default=6, description="Short-term window rounds during call")
    compress_trigger_rounds: int = Field(default=6, description="Compression trigger rounds")
    compress_trigger_chars: int = Field(default=1500, description="Compression trigger chars")
    summary_max_chars: int = Field(default=600, description="Max chars of mid-term summary")


class VoiceGatewayOmniConfig(BaseModel):
    realtime_enabled: bool = Field(default=True, description="Enable Omni realtime")
    ws_url: str = Field(default="wss://dashscope.aliyuncs.com/api-ws/v1/realtime", description="Omni realtime ws url")
    api_key: str = Field(default="", description="Omni realtime api key")
    model: str = Field(default="qwen", description="Omni model id")
    input_transcription_model: str = Field(default="qwen3-asr-flash-realtime", description="Realtime ASR model")
    # This gateway currently uses a manual turn flow:
    # input_audio_buffer.append -> commit -> response.create.
    # Keep upstream turn detection disabled by default.
    turn_detection_type: str = Field(default="none", description="Turn detection type, recommend none")
    vad_threshold: float = Field(default=0.5, description="Upstream VAD threshold")
    vad_prefix_padding_ms: int = Field(default=300, description="Upstream VAD prefix padding in milliseconds")
    vad_silence_duration_ms: int = Field(default=500, description="Upstream VAD silence duration in milliseconds")
    request_timeout_seconds: int = Field(default=60, description="Per-turn timeout in seconds")


class VoiceGatewayTTSConfig(BaseModel):
    enabled: bool = Field(default=True, description="Enable TTS")
    realtime_enabled: bool = Field(default=True, description="Enable TTS realtime")
    ws_url: str = Field(default="wss://dashscope.aliyuncs.com/api-ws/v1/realtime", description="TTS realtime ws url")
    api_key: str = Field(default="", description="TTS realtime api key")
    model: str = Field(default="qwen3-tts-vc-realtime-2025-11-27", description="TTS realtime model")
    voice: str = Field(default="", description="TTS voice id")


class VoiceGatewayObservabilityConfig(BaseModel):
    trace_enabled: bool = Field(default=True, description="Enable trace logging")


class VoiceGatewayConfig(BaseModel):
    enabled: bool = Field(default=False, description="Voice gateway switch")
    ws: VoiceGatewayWSConfig = Field(default_factory=VoiceGatewayWSConfig)
    auth: VoiceGatewayAuthConfig = Field(default_factory=VoiceGatewayAuthConfig)
    call: VoiceGatewayCallConfig = Field(default_factory=VoiceGatewayCallConfig)
    audio: VoiceGatewayAudioConfig = Field(default_factory=VoiceGatewayAudioConfig)
    memory: VoiceGatewayMemoryConfig = Field(default_factory=VoiceGatewayMemoryConfig)
    omni: VoiceGatewayOmniConfig = Field(default_factory=VoiceGatewayOmniConfig)
    tts: VoiceGatewayTTSConfig = Field(default_factory=VoiceGatewayTTSConfig)
    observability: VoiceGatewayObservabilityConfig = Field(default_factory=VoiceGatewayObservabilityConfig)

    @classmethod
    def from_dict(cls, value: Dict[str, Any]) -> "VoiceGatewayConfig":
        return cls(**(value or {}))
