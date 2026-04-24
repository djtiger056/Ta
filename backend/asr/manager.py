from typing import Optional, Dict, Any, Union
from .config import ASRConfig
from .providers.siliconflow_asr import SiliconFlowASRProvider
from .providers.qwen_asr import QwenASRProvider


class ASRManager:
    """ASR语音识别管理器"""

    def __init__(self, config: ASRConfig):
        self.config = config
        self.provider = self._create_provider()

    def _create_provider(self):
        """创建ASR提供商实例"""
        if self.config.provider == "siliconflow":
            return SiliconFlowASRProvider(self.config.siliconflow.dict())
        elif self.config.provider == "qwen":
            return QwenASRProvider(self.config.qwen.dict())
        else:
            raise ValueError(f"不支持的ASR提供商: {self.config.provider}")

    def update_config(self, config: Union[ASRConfig, Dict[str, Any]]):
        """更新配置并重建提供商"""
        if isinstance(config, ASRConfig):
            self.config = config
        else:
            self.config = ASRConfig(**config)
        self.provider = self._create_provider()

    async def transcribe_audio(self, audio_data: bytes, filename: str = "audio.mp3") -> str:
        """
        语音转文本

        Args:
            audio_data: 音频文件的二进制数据
            filename: 文件名

        Returns:
            识别结果文本
        """
        try:
            return await self.provider.transcribe(audio_data, filename)
        except Exception as e:
            print(f"语音识别失败: {str(e)}")
            raise Exception(f"语音识别失败: {str(e)}")

    async def test_connection(self) -> bool:
        """测试连接"""
        try:
            return await self.provider.test_connection()
        except Exception as e:
            print(f"测试连接失败: {str(e)}")
            return False
