import aiohttp
import asyncio
import json
import base64
from io import BytesIO
from PIL import Image
from tests._secrets import require_api_key

async def test_image_generation():
    api_key = require_api_key("YUNWU_API_KEY", "云舞图像生成测试")
    api_base = "https://yunwu.ai/v1"
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    url = f"{api_base}/images/generations"
    
    data = {
        "model": "jimeng-4.5",
        "prompt": "一只小猫",
        "n": 1,
        "size": "1024x1024"
    }
    
    timeout = aiohttp.ClientTimeout(total=120)
    
    try:
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(url, headers=headers, json=data) as response:
                print(f"状态码: {response.status}")
                response_text = await response.text()
                print(f"响应: {response_text}")
                if response.status == 200:
                    result = json.loads(response_text)
                    print("图像生成成功")
                    # 检查返回的数据
                    if 'data' in result and len(result['data']) > 0:
                        image_data = result['data'][0]
                        if 'url' in image_data:
                            print(f"图片URL: {image_data['url']}")
                        elif 'b64_json' in image_data:
                            print("收到base64图像数据")
                    return True
                else:
                    print("图像生成失败")
                    return False
    except Exception as e:
        print(f"请求异常: {e}")
        return False

if __name__ == "__main__":
    result = asyncio.run(test_image_generation())
    exit(0 if result else 1)
