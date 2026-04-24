import aiohttp
import asyncio
from typing import Optional, Dict, Any


class SiliconFlowASRProvider:
    """硅基流动ASR提供商"""

    def __init__(self, config: Dict[str, Any]):
        self.api_base = config.get('api_base', 'https://api.siliconflow.cn/v1')
        self.api_key = config.get('api_key', '')
        self.model = config.get('model', 'FunAudioLLM/SenseVoiceSmall')
        self.timeout = config.get('timeout', 30)

        if not self.api_key:
            raise ValueError("硅基流动API密钥未配置")

    async def transcribe(self, audio_data: bytes, filename: str = "audio.mp3") -> str:
        """
        语音转文本

        Args:
            audio_data: 音频文件的二进制数据
            filename: 文件名（用于API请求）

        Returns:
            识别结果文本
        """
        url = f"{self.api_base}/audio/transcriptions"

        headers = {
            "Authorization": f"Bearer {self.api_key}"
        }

        # 使用aiohttp的FormData构建multipart/form-data请求
        form_data = aiohttp.FormData()
        form_data.add_field('file', audio_data, filename=filename, content_type='audio/mpeg')
        form_data.add_field('model', self.model)

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url,
                    data=form_data,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=self.timeout)
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise Exception(f"ASR API请求失败 (HTTP {response.status}): {error_text}")

                    result = await response.json()

                    # 从响应中提取转录文本
                    if 'text' in result:
                        return result['text']
                    else:
                        raise Exception(f"API响应格式错误: {result}")

        except asyncio.TimeoutError:
            raise Exception("语音识别超时")
        except aiohttp.ClientError as e:
            raise Exception(f"网络请求失败: {str(e)}")
        except Exception as e:
            raise Exception(f"语音识别失败: {str(e)}")

    async def test_connection(self) -> bool:
        """测试连接"""
        # 由于ASR需要音频文件才能测试，这里只检查配置是否有效
        return bool(self.api_key)
