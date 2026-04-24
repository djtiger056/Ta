import base64
import io
from typing import Optional, Dict, Any
from openai import AsyncOpenAI
from .base import BaseVisionProvider


class ModelScopeVisionProvider(BaseVisionProvider):
    """魔搭社区视觉识别提供商"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.api_key = config.get('api_key', '')
        self.model = config.get('model', 'Qwen/Qwen3-VL-30B-A3B-Instruct')
        self.base_url = config.get('base_url', 'https://api-inference.modelscope.cn/v1')
        self.timeout = config.get('timeout', 120)
        
        self.client = AsyncOpenAI(
            base_url=self.base_url,
            api_key=self.api_key,
            timeout=self.timeout
        )
    
    async def recognize(self, image_url: Optional[str] = None, image_data: Optional[bytes] = None,
                       prompt: str = "描述这幅图") -> str:
        """
        识别图片
        
        Args:
            image_url: 图片URL
            image_data: 图片二进制数据
            prompt: 识别提示词
            
        Returns:
            识别结果文本
        """
        if not image_url and not image_data:
            raise ValueError("必须提供image_url或image_data")
        
        # 构建消息内容
        content = []
        if prompt:
            content.append({
                "type": "text",
                "text": prompt
            })
        
        if image_url:
            content.append({
                "type": "image_url",
                "image_url": {
                    "url": image_url
                }
            })
        else:
            # 将图片数据转换为base64
            base64_data = base64.b64encode(image_data).decode('utf-8')
            # 构建data URL
            image_mime = self._detect_image_mime(image_data)
            data_url = f"data:{image_mime};base64,{base64_data}"
            content.append({
                "type": "image_url",
                "image_url": {
                    "url": data_url
                }
            })
        
        messages = [{
            "role": "user",
            "content": content
        }]
        
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                stream=False
            )
            
            if response.choices and len(response.choices) > 0:
                return response.choices[0].message.content or ""
            else:
                return ""
        except Exception as e:
            raise Exception(f"图片识别失败: {str(e)}")

    @staticmethod
    def _detect_image_mime(image_data: Optional[bytes]) -> str:
        if not image_data:
            return "image/jpeg"
        if image_data.startswith(b"\xff\xd8\xff"):
            return "image/jpeg"
        if image_data.startswith(b"\x89PNG\r\n\x1a\n"):
            return "image/png"
        if image_data.startswith((b"GIF87a", b"GIF89a")):
            return "image/gif"
        if image_data.startswith(b"BM"):
            return "image/bmp"
        if image_data[:4] == b"RIFF" and image_data[8:12] == b"WEBP":
            return "image/webp"
        if image_data.startswith((b"II*\x00", b"MM\x00*")):
            return "image/tiff"
        return "image/jpeg"
    
    async def test_connection(self) -> bool:
        """测试连接"""
        try:
            # 发送一个简单的测试请求
            test_messages = [{
                "role": "user",
                "content": [
                    {"type": "text", "text": "描述这幅图"},
                    {"type": "image_url", "image_url": {
                        "url": "https://modelscope.oss-cn-beijing.aliyuncs.com/demo/images/audrey_hepburn.jpg"
                    }}
                ]
            }]
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=test_messages,
                stream=False,
                max_tokens=10
            )
            return True
        except Exception as e:
            print(f"视觉识别连接测试失败: {str(e)}")
            return False
