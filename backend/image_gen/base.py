from abc import ABC, abstractmethod
from typing import Optional, Dict, Any


class BaseImageProvider(ABC):
    """图像生成提供商基础接口"""
    
    @abstractmethod
    async def generate(self, prompt: str) -> Optional[bytes]:
        """生成图像
        
        Args:
            prompt: 图像生成提示词
            
        Returns:
            图像二进制数据，失败返回None
        """
        pass
    
    @abstractmethod
    async def test_connection(self) -> bool:
        """测试连接
        
        Returns:
            连接是否成功
        """
        pass