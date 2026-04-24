from typing import Dict, Any, Optional
from pydantic import BaseModel


class SiliconFlowASRConfig(BaseModel):
    """硅基流动ASR配置"""
    api_base: str = "https://api.siliconflow.cn/v1"
    api_key: str = ""
    model: str = "FunAudioLLM/SenseVoiceSmall"
    timeout: int = 30


class QwenASRConfig(BaseModel):
    """千问（DashScope）ASR配置"""
    api_base: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    api_key: str = ""
    model: str = "qwen3-asr-flash"
    timeout: int = 30


class ASRConfig(BaseModel):
    """ASR语音识别配置"""
    enabled: bool = False
    provider: str = "siliconflow"  # 当前提供商
    siliconflow: SiliconFlowASRConfig = SiliconFlowASRConfig()
    qwen: QwenASRConfig = QwenASRConfig()
    # 是否自动发送识别结果给LLM
    auto_send_to_llm: bool = True
    # 处理中消息
    processing_message: str = "正在识别语音..."
    # 错误消息模板
    error_message: str = "语音识别失败了呢"
