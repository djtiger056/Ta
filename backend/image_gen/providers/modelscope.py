import asyncio
import time
import json
import requests
from PIL import Image
from io import BytesIO
from typing import Optional, Dict, Any
from ..base import BaseImageProvider


class ModelScopeProvider(BaseImageProvider):
    """魔搭社区图像生成提供商"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.base_url = 'https://api-inference.modelscope.cn/'
        self.api_key = config.get('api_key', '')
        self.model = config.get('model', 'Tongyi-MAI/Z-Image-Turbo')
        self.timeout = config.get('timeout', 120)
        
    async def generate(self, prompt: str) -> Optional[bytes]:
        """生成图像"""
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }
            
            # 提交图像生成任务
            response = requests.post(
                f"{self.base_url}v1/images/generations",
                headers={**headers, "X-ModelScope-Async-Mode": "true"},
                data=json.dumps({
                    "model": self.model,
                    "prompt": prompt
                }, ensure_ascii=False).encode('utf-8')
            )
            
            response.raise_for_status()
            task_id = response.json()["task_id"]
            
            # 轮询任务状态
            start_time = time.time()
            while time.time() - start_time < self.timeout:
                result = requests.get(
                    f"{self.base_url}v1/tasks/{task_id}",
                    headers={**headers, "X-ModelScope-Task-Type": "image_generation"},
                )
                result.raise_for_status()
                data = result.json()
                
                if data["task_status"] == "SUCCEED":
                    # 下载图像
                    image_response = requests.get(data["output_images"][0])
                    image_response.raise_for_status()
                    
                    # 转换为bytes
                    image = Image.open(BytesIO(image_response.content))
                    img_buffer = BytesIO()
                    image.save(img_buffer, format='JPEG')
                    return img_buffer.getvalue()
                    
                elif data["task_status"] == "FAILED":
                    return None
                
                await asyncio.sleep(5)
            
            return None
            
        except Exception as e:
            print(f"魔搭社区图像生成失败: {str(e)}")
            return None
    
    async def test_connection(self) -> bool:
        """测试连接"""
        try:
            result = await self.generate("测试图片：一只小猫")
            return result is not None
        except:
            return False