import aiohttp
import asyncio
import json
from tests._secrets import require_api_key

async def list_models():
    api_key = require_api_key("YUNWU_API_KEY", "云舞模型列表测试")
    api_base = "https://yunwu.ai/v1"
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    url = f"{api_base}/models"
    
    timeout = aiohttp.ClientTimeout(total=30)
    
    try:
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"找到 {len(data.get('data', []))} 个模型")
                    print("\n模型列表:")
                    for model in data.get('data', []):
                        model_id = model.get('id', '')
                        owned_by = model.get('owned_by', '')
                        endpoint_types = model.get('supported_endpoint_types', [])
                        print(f"- {model_id} (属于: {owned_by}, 端点: {endpoint_types})")
                    
                    # 查找 jimeng-4.5
                    jimeng_models = [m for m in data.get('data', []) if 'jimeng' in model_id.lower()]
                    if jimeng_models:
                        print(f"\n找到 jimeng 模型: {[m['id'] for m in jimeng_models]}")
                    else:
                        print("\n未找到 jimeng 模型")
                        
                    # 检查是否有图像生成端点
                    image_models = [m for m in data.get('data', []) if any('image' in str(et).lower() for et in m.get('supported_endpoint_types', []))]
                    print(f"\n找到 {len(image_models)} 个支持图像生成的模型:")
                    for model in image_models:
                        print(f"- {model['id']} (端点: {model['supported_endpoint_types']})")
                        
                else:
                    print(f"状态码: {response.status}")
                    print(await response.text())
    except Exception as e:
        print(f"请求异常: {e}")

if __name__ == "__main__":
    asyncio.run(list_models())
