from abc import ABC, abstractmethod
from typing import Optional, Dict, Any


class BaseVisionProvider(ABC):
    """视觉识别提供商基类"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
    
    @abstractmethod
    async def recognize(self, image_url: Optional[str] = None, image_data: Optional[bytes] = None, 
                       prompt: str = "描述这幅图") -> str:
        """
        识别图片
        
        Args:
            image_url: 图片URL
            image_data: 图片二进制数据（如果提供image_url则忽略）
            prompt: 识别提示词
            
        Returns:
            识别结果文本
        """
        pass
    
    @abstractmethod
    async def test_connection(self) -> bool:
        """测试连接"""
        pass