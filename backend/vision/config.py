from typing import Dict, Any, List, Optional
from pydantic import BaseModel


class ModelScopeVisionConfig(BaseModel):
    """魔搭社区视觉识别配置"""
    api_key: str = ""
    model: str = "Qwen/Qwen3-VL-30B-A3B-Instruct"  # 默认模型
    base_url: str = "https://api-inference.modelscope.cn/v1"
    timeout: int = 120
    # 其他参数如 temperature 等可根据需要添加


class VisionRecognitionConfig(BaseModel):
    """视觉识别配置"""
    enabled: bool = False
    provider: str = "modelscope"  # 当前提供商
    modelscope: ModelScopeVisionConfig = ModelScopeVisionConfig()
    # 特殊文本，用于指导LLM生成合适的话语
    instruction_text: str = "这是一张图片的描述，请根据描述生成一段合适的话语："
    # 是否自动发送识别结果给LLM
    auto_send_to_llm: bool = True
    # 图片识别后等待用户补充消息的超时时间（秒）
    follow_up_timeout: float = 5.0
    # 触发关键词（可选，可用于文本触发识别）
    trigger_keywords: List[str] = ["识别图片", "描述图片", "这是什么图"]
    # 错误消息模板
    error_message: str = "😢 图片识别失败：{error}"