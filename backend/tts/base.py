"""
TTS 提供商基础接口
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
import asyncio


class BaseTTSProvider(ABC):
    """TTS 提供商基础接口"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
    
    @abstractmethod
    async def synthesize(self, text: str, voice: Optional[str] = None) -> bytes:
        """
        合成语音
        
        Args:
            text: 要合成的文本
            voice: 语音角色，可选
            
        Returns:
            bytes: 音频数据
            
        Raises:
            Exception: 合成失败时抛出异常
        """
        pass
    
    @abstractmethod
    async def get_voices(self) -> List[Dict[str, str]]:
        """
        获取可用语音角色列表
        
        Returns:
            List[Dict[str, str]]: 语音角色列表，包含 name 和 description
        """
        pass
    
    @abstractmethod
    async def test_connection(self) -> bool:
        """
        测试连接
        
        Returns:
            bool: 连接是否成功
        """
        pass
    
    def get_default_voice(self) -> str:
        """获取默认语音角色"""
        return self.config.get('voice', '柔情萝莉')
    
    def get_model(self) -> str:
        """获取模型名称"""
        return self.config.get('model', 'qhai-tts')
    
    def get_api_key(self) -> str:
        """获取API密钥"""
        return self.config.get('api_key', '')
    
    def get_api_base(self) -> str:
        """获取API基础URL"""
        return self.config.get('api_base', 'https://api.qhaigc.net/v1')