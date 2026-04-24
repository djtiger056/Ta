import re
from typing import Optional, Dict, Any
from .config import ImageGenerationConfig
from .providers.modelscope import ModelScopeProvider
from .providers.yunwu import YunwuProvider


class ImageGenerationManager:
    """图像生成管理器"""

    def __init__(self, config: ImageGenerationConfig):
        self.config = config
        self.primary_provider = self._create_provider(self.config.provider)
        self.fallback_provider = None
        if self.config.enable_fallback and self.config.fallback_provider != self.config.provider:
            try:
                self.fallback_provider = self._create_provider(self.config.fallback_provider)
                print(f"[ImageGen] 已初始化备用提供商: {self.config.fallback_provider}")
            except Exception as e:
                print(f"[ImageGen] 初始化备用提供商失败: {e}")

    def _create_provider(self, provider_name: str):
        """创建图像生成提供商实例"""
        if provider_name == "modelscope":
            return ModelScopeProvider(self.config.modelscope.dict())
        elif provider_name == "yunwu":
            return YunwuProvider(self.config.yunwu.dict())
        else:
            raise ValueError(f"不支持的图像生成提供商: {provider_name}")

    def update_config(self, config: ImageGenerationConfig):
        """更新配置"""
        self.config = config
        self.primary_provider = self._create_provider(self.config.provider)
        self.fallback_provider = None
        if self.config.enable_fallback and self.config.fallback_provider != self.config.provider:
            try:
                self.fallback_provider = self._create_provider(self.config.fallback_provider)
                print(f"[ImageGen] 已更新备用提供商: {self.config.fallback_provider}")
            except Exception as e:
                print(f"[ImageGen] 更新备用提供商失败: {e}")
    
    def should_trigger_image_generation(self, message: str) -> Optional[str]:
        """检查是否应该触发图像生成
        
        Args:
            message: 用户消息
            
        Returns:
            提取的提示词，如果不触发则返回None
        """
        if not self.config.enabled:
            return None
        
        message = message.strip()
        
        # 检查触发关键词
        for keyword in self.config.trigger_keywords:
            if keyword in message:
                # 提取提示词
                prompt = self._extract_prompt(message, keyword)
                if prompt:
                    return prompt
        
        return None
    
    def _extract_prompt(self, message: str, keyword: str) -> Optional[str]:
        """从消息中提取提示词"""
        # 简单的提示词提取逻辑
        patterns = [
            rf"{keyword}[:：]\s*(.+)",  # 画：xxx 或 生成图片：xxx
            rf"{keyword}(.+)",          # 画xxx 或 生成图片xxx
            rf"帮我{keyword}(.+)",       # 帮我画xxx
            rf"请{keyword}(.+)",        # 请画xxx
            rf"{keyword}，(.+)",        # 画，xxx
        ]
        
        # 特殊模式：处理"帮我生图，主题是xxx"这样的格式
        special_patterns = [
            r"帮我生图[，,]\s*主题是\s*(.+)",  # 帮我生图，主题是xxx
            r"请生图[，,]\s*主题是\s*(.+)",   # 请生图，主题是xxx
            r"生图[，,]\s*主题是\s*(.+)",     # 生图，主题是xxx
        ]
        
        # 先检查特殊模式
        for pattern in special_patterns:
            match = re.search(pattern, message, re.IGNORECASE)
            if match:
                prompt = match.group(1).strip()
                # 移除末尾的标点符号
                prompt = re.sub(r'[。，！？,.!?]+$', '', prompt)
                if prompt:
                    return prompt
        
        # 再检查常规模式
        for pattern in patterns:
            match = re.search(pattern, message, re.IGNORECASE)
            if match:
                prompt = match.group(1).strip()
                # 移除末尾的标点符号
                prompt = re.sub(r'[。，！？,.!?]+$', '', prompt)
                if prompt:
                    return prompt
        
        return None
    
    async def generate_image(self, prompt: str) -> Optional[bytes]:
        """生成图像（支持自动降级）"""
        # 先尝试主提供商
        try:
            result = await self.primary_provider.generate(prompt)
            if result:
                print(f"[ImageGen] 主提供商 {self.config.provider} 生成成功")
                return result
        except Exception as e:
            print(f"[ImageGen] 主提供商 {self.config.provider} 失败: {str(e)}")

        # 如果主提供商失败且启用了降级，尝试备用提供商
        if self.config.enable_fallback and self.fallback_provider:
            print(f"[ImageGen] 切换到备用提供商 {self.config.fallback_provider}")
            try:
                result = await self.fallback_provider.generate(prompt)
                if result:
                    print(f"[ImageGen] 备用提供商 {self.config.fallback_provider} 生成成功")
                    return result
                else:
                    print(f"[ImageGen] 备用提供商 {self.config.fallback_provider} 返回空结果")
            except Exception as e:
                print(f"[ImageGen] 备用提供商 {self.config.fallback_provider} 失败: {str(e)}")
        else:
            if not self.config.enable_fallback:
                print(f"[ImageGen] 自动降级未启用")
            elif not self.fallback_provider:
                print(f"[ImageGen] 未配置备用提供商")

        print(f"[ImageGen] 所有提供商均失败")
        return None
    
    async def test_connection(self) -> bool:
        """测试连接（支持降级）"""
        # 先测试主提供商
        try:
            if await self.primary_provider.test_connection():
                print(f"[ImageGen] 主提供商 {self.config.provider} 连接正常")
                return True
        except Exception as e:
            print(f"[ImageGen] 主提供商 {self.config.provider} 连接失败: {str(e)}")

        # 如果主提供商失败且启用了降级，测试备用提供商
        if self.config.enable_fallback and self.fallback_provider:
            try:
                if await self.fallback_provider.test_connection():
                    print(f"[ImageGen] 备用提供商 {self.config.fallback_provider} 连接正常")
                    return True
            except Exception as e:
                print(f"[ImageGen] 备用提供商 {self.config.fallback_provider} 连接失败: {str(e)}")

        return False