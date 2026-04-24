"""
TTS 语音合成系统
"""

from .manager import TTSManager
from .providers.qihang import QihangTTSProvider
from .providers.qwen import QwenTTSProvider

__all__ = [
    "TTSManager",
    "QihangTTSProvider",
    "QwenTTSProvider",
]
