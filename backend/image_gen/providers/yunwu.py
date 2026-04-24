import aiohttp
from aiohttp import ClientTimeout
from PIL import Image
from io import BytesIO
from typing import Optional, Dict, Any
from ..base import BaseImageProvider


class YunwuProvider(BaseImageProvider):
    """yunwu.ai 图像生成提供商"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.base_url = config.get('api_base', 'https://yunwu.ai/v1')
        self.api_key = config.get('api_key', '')
        self.model = config.get('model', 'jimeng-4.5')
        self.timeout = config.get('timeout', 120)

    async def generate(self, prompt: str) -> Optional[bytes]:
        """生成图像"""
        try:
            url = f"{self.base_url}/images/generations"

            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }

            data = {
                "model": self.model,
                "prompt": prompt,
                "n": 1,
                "size": "1024x1024"
            }

            # 配置详细的超时设置（与 openai_provider 一致）
            timeout = ClientTimeout(
                connect=10,      # 连接超时 10秒
                sock_connect=10, # socket连接超时 10秒
                sock_read=self.timeout,  # 读取超时（使用配置的超时时间）
                total=self.timeout + 20  # 总超时（配置超时 + 20秒缓冲）
            )

            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(url, headers=headers, json=data) as response:
                    if response.status == 200:
                        result = await response.json()

                        # 获取图片URL或base64数据
                        if 'data' in result and len(result['data']) > 0:
                            image_data = result['data'][0]

                            # 如果返回的是URL，需要下载图片
                            if 'url' in image_data:
                                image_url = image_data['url']
                                async with session.get(image_url) as img_response:
                                    if img_response.status == 200:
                                        image_bytes = await img_response.read()
                                        # 转换为JPEG格式
                                        image = Image.open(BytesIO(image_bytes))
                                        img_buffer = BytesIO()
                                        image.save(img_buffer, format='JPEG')
                                        return img_buffer.getvalue()

                            # 如果返回的是base64数据
                            elif 'b64_json' in image_data:
                                import base64
                                image_bytes = base64.b64decode(image_data['b64_json'])
                                # 转换为JPEG格式
                                image = Image.open(BytesIO(image_bytes))
                                img_buffer = BytesIO()
                                image.save(img_buffer, format='JPEG')
                                return img_buffer.getvalue()

                        return None
                    else:
                        error_text = await response.text()
                        print(f"yunwu.ai 图像生成失败: {response.status} - {error_text}")
                        return None

        except aiohttp.ClientError as e:
            print(f"yunwu.ai 图像生成网络错误: {str(e)}")
            return None
        except Exception as e:
            print(f"yunwu.ai 图像生成失败: {str(e)}")
            return None

    async def test_connection(self) -> bool:
        """测试连接"""
        try:
            result = await self.generate("测试图片：一只小猫")
            return result is not None
        except:
            return False
