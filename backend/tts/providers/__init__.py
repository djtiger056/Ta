"""
TTS 提供商实现
"""

from .qihang import QihangTTSProvider
from .qwen import QwenTTSProvider

__all__ = [
    "QihangTTSProvider",
    "QwenTTSProvider",
]
