from abc import ABC, abstractmethod
from typing import Dict, Any, AsyncGenerator


class BaseLLMProvider(ABC):
    """LLM提供商基础接口"""
    
    @abstractmethod
    async def chat(self, messages: list, **kwargs) -> str:
        """发送聊天消息并获取回复"""
        pass
    
    @abstractmethod
    async def chat_stream(self, messages: list, **kwargs) -> AsyncGenerator[str, None]:
        """流式聊天回复"""
        pass
    
    @abstractmethod
    async def test_connection(self) -> bool:
        """测试API连接"""
        pass