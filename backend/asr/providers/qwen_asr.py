import aiohttp
import asyncio
import base64
import mimetypes
from typing import Dict, Any, Optional


class QwenASRProvider:
    """千问（DashScope OpenAI兼容）ASR提供商"""

    def __init__(self, config: Dict[str, Any]):
        self.api_base = config.get('api_base', 'https://dashscope.aliyuncs.com/compatible-mode/v1')
        self.api_key = config.get('api_key', '')
        self.model = config.get('model', 'qwen3-asr-flash')
        self.timeout = config.get('timeout', 30)

        if not self.api_key:
            raise ValueError("千问ASR API密钥未配置")

    async def transcribe(self, audio_data: bytes, filename: str = "audio.mp3") -> str:
        """语音转文本（DashScope OpenAI兼容：chat/completions + input_audio）"""
        url = f"{self.api_base}/chat/completions"
        mime_type = self._guess_mime_type(filename)
        audio_base64 = base64.b64encode(audio_data).decode('utf-8')
        data_url = f"data:{mime_type};base64,{audio_base64}"

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_audio",
                            "input_audio": {
                                "data": data_url,
                            }
                        }
                    ]
                }
            ],
            "stream": False,
            "asr_options": {
                "enable_itn": False,
            }
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url,
                    json=payload,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=self.timeout)
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise Exception(f"ASR API请求失败 (HTTP {response.status}): {error_text}")

                    result = await response.json()
                    transcription_text = self._extract_transcription_text(result)
                    if transcription_text:
                        return transcription_text

                # 兼容模式重试：部分网关更偏好原始 base64 + format，而非 data URL
                payload_retry = {
                    "model": self.model,
                    "messages": [
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "input_audio",
                                    "input_audio": {
                                        "data": audio_base64,
                                        "format": self._mime_to_format(mime_type),
                                    }
                                }
                            ]
                        }
                    ],
                    "stream": False,
                    "asr_options": {
                        "enable_itn": False,
                    }
                }
                async with session.post(
                    url,
                    json=payload_retry,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=self.timeout)
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise Exception(f"ASR API请求失败 (HTTP {response.status}): {error_text}")
                    result = await response.json()
                    transcription_text = self._extract_transcription_text(result)
                    return transcription_text or ""

        except asyncio.TimeoutError:
            raise Exception("语音识别超时")
        except aiohttp.ClientError as e:
            raise Exception(f"网络请求失败: {str(e)}")
        except Exception as e:
            raise Exception(f"语音识别失败: {str(e)}")

    async def test_connection(self) -> bool:
        """测试连接"""
        return bool(self.api_key)

    @staticmethod
    def _guess_mime_type(filename: str) -> str:
        mime_type, _ = mimetypes.guess_type(filename)
        return mime_type or 'audio/mpeg'

    @staticmethod
    def _mime_to_format(mime_type: str) -> str:
        mime_type = (mime_type or "").lower()
        if "wav" in mime_type:
            return "wav"
        if "pcm" in mime_type:
            return "pcm"
        if "ogg" in mime_type:
            return "ogg"
        if "webm" in mime_type:
            return "webm"
        if "m4a" in mime_type or "mp4" in mime_type:
            return "m4a"
        return "mp3"

    @staticmethod
    def _extract_transcription_text(result: Dict[str, Any]) -> Optional[str]:
        # 兼容潜在的直出字段
        output_text = result.get("output_text")
        if isinstance(output_text, str) and output_text.strip():
            return output_text.strip()

        choices = result.get('choices')
        if not isinstance(choices, list) or not choices:
            return None

        first_choice = choices[0] if isinstance(choices[0], dict) else {}
        message = first_choice.get('message') if isinstance(first_choice, dict) else {}

        # 兼容 message.audio.transcript 结构
        audio_obj = message.get("audio") if isinstance(message, dict) else None
        if isinstance(audio_obj, dict):
            transcript = audio_obj.get("transcript")
            if isinstance(transcript, str) and transcript.strip():
                return transcript.strip()

        content = message.get('content') if isinstance(message, dict) else None

        if isinstance(content, str):
            text = content.strip()
            return text or None

        if isinstance(content, list):
            parts = []
            for item in content:
                if not isinstance(item, dict):
                    continue
                candidate = item.get('text') or item.get('content')
                if isinstance(candidate, str) and candidate.strip():
                    parts.append(candidate.strip())
            merged_text = '\n'.join(parts).strip()
            return merged_text or None

        return None
