from typing import Dict, Any, List, Optional
from pydantic import BaseModel


class ModelScopeConfig(BaseModel):
    """魔搭社区配置"""
    api_key: str = ""
    model: str = "Tongyi-MAI/Z-Image-Turbo"
    timeout: int = 120


class YunwuConfig(BaseModel):
    """yunwu.ai 配置"""
    api_key: str = ""
    api_base: str = "https://yunwu.ai/v1"
    model: str = "jimeng-4.5"
    timeout: int = 120


class ImageGenerationConfig(BaseModel):
    """图像生成配置"""
    enabled: bool = False
    provider: str = "modelscope"  # 当前提供商
    fallback_provider: str = "yunwu"  # 备用提供商
    enable_fallback: bool = True  # 是否启用自动降级
    modelscope: ModelScopeConfig = ModelScopeConfig()
    yunwu: YunwuConfig = YunwuConfig()
    trigger_keywords: List[str] = [
        "画", "生成图片", "生图", "绘制"
    ]
    generating_message: str = "🎨 正在为你生成图片，请稍候..."
    error_message: str = "😢 图片生成失败：{error}"
    success_message: str = "✨ 图片已生成完成！"