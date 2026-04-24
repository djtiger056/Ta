import re
from typing import Optional, Dict, Any
from .config import VisionRecognitionConfig
from .providers.modelscope_vision import ModelScopeVisionProvider


class VisionRecognitionManager:
    """视觉识别管理器"""
    
    def __init__(self, config: VisionRecognitionConfig):
        self.config = config
        self.provider = self._create_provider()
    
    def _create_provider(self):
        """创建视觉识别提供商实例"""
        if self.config.provider == "modelscope":
            return ModelScopeVisionProvider(self.config.modelscope.dict())
        else:
            raise ValueError(f"不支持的视觉识别提供商: {self.config.provider}")
    
    def update_config(self, config: VisionRecognitionConfig):
        """更新配置"""
        print(f"[DEBUG] VisionManager.update_config - follow_up_timeout: {config.follow_up_timeout}")
        self.config = config
        self.provider = self._create_provider()
    
    def should_trigger_vision_recognition(self, message_segments: list) -> bool:
        """
        检查是否应该触发视觉识别
        
        Args:
            message_segments: 消息段列表，每个元素是字典，包含type和data
            
        Returns:
            是否触发识别
        """
        if not self.config.enabled:
            return False
        
        # 检查消息中是否包含图片段
        for segment in message_segments:
            if isinstance(segment, dict) and segment.get('type') == 'image':
                return True
        
        return False
    
    async def recognize_image(self, image_url: Optional[str] = None, image_data: Optional[bytes] = None,
                             prompt: Optional[str] = None) -> str:
        """
        识别图片
        
        Args:
            image_url: 图片URL
            image_data: 图片二进制数据
            prompt: 识别提示词，如果为None则使用默认提示词
            
        Returns:
            识别结果文本
        """
        try:
            if prompt is None:
                prompt = "描述这幅图"
            return await self.provider.recognize(image_url, image_data, prompt)
        except Exception as e:
            print(f"图片识别失败: {str(e)}")
            raise Exception(f"图片识别失败: {str(e)}")
    
    async def test_connection(self) -> bool:
        """测试连接"""
        try:
            return await self.provider.test_connection()
        except Exception as e:
            print(f"测试连接失败: {str(e)}")
            return False