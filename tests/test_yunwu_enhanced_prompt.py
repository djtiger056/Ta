import aiohttp
import asyncio
import json
from tests._secrets import require_api_key

async def test_image_generation_with_prompt(prompt):
    api_key = require_api_key("YUNWU_API_KEY", "云舞增强提示测试")
    api_base = "https://yunwu.ai/v1"
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    url = f"{api_base}/images/generations"
    
    data = {
        "model": "jimeng-4.5",
        "prompt": prompt,
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
                    print("图像生成成功")
                    return True
                else:
                    print("图像生成失败")
                    return False
    except Exception as e:
        print(f"请求异常: {e}")
        return False

if __name__ == "__main__":
    enhanced_prompt = "自拍照，日常快照风格，略带模糊感，空气刘海长发，一位约20岁的女大学生，面部轮廓为标准鹅蛋脸，肤色冷白，五官精致甜美，眼神清澈带微羞感，呈现“纯欲风”视觉气质；鬓角两侧有细碎发丝自然飘拂，发质柔顺微卷，碎花连衣裙，公园草地，全身照"
    print(f"测试提示词: {enhanced_prompt}")
    result = asyncio.run(test_image_generation_with_prompt(enhanced_prompt))
    exit(0 if result else 1)
