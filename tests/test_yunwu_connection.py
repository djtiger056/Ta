import aiohttp
import asyncio
import sys
from tests._secrets import require_api_key

async def test_connection():
    api_key = require_api_key("YUNWU_API_KEY", "云舞连接测试")
    api_base = "https://yunwu.ai/v1"
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    # 测试 /models 端点
    url = f"{api_base}/models"
    
    timeout = aiohttp.ClientTimeout(total=30)
    
    try:
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(url, headers=headers) as response:
                print(f"状态码: {response.status}")
                response_text = await response.text()
                print(f"响应: {response_text}")
                if response.status == 200:
                    print("连接成功，API密钥有效")
                    return True
                else:
                    print("连接失败，API密钥无效或服务不可用")
                    return False
    except Exception as e:
        print(f"请求异常: {e}")
        return False

if __name__ == "__main__":
    result = asyncio.run(test_connection())
    sys.exit(0 if result else 1)
