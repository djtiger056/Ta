import asyncio
import aiohttp
import json
from tests._secrets import require_api_key

async def test():
    api_key = require_api_key("QHAIGC_API_KEY", "语音模型列表测试")
    headers = {'Authorization': api_key}

    # 尝试不同的路径
    endpoints = [
        'https://api.qhaigc.net/v1/voice/models/list',
        'https://api.qhaigc.net/v1/voices',
        'https://api.qhaigc.net/v1/voice/list',
        'https://api.qhaigc.net/v1/models/voices',
        'https://api.qhaigc.net/audio/voices',
    ]

    async with aiohttp.ClientSession() as session:
        for endpoint in endpoints:
            try:
                async with session.get(endpoint, headers=headers) as resp:
                    print(f'\n=== Testing: {endpoint} ===')
                    print(f'Status: {resp.status}')
                    if resp.status == 200:
                        data = await resp.json()
                        print(f'Success! Voice count: {len(data.get("voice_characters", data.get("voices", data.get("data", []))))}')
                        print(json.dumps(data, ensure_ascii=False, indent=2))
                        break
                    else:
                        text = await resp.text()
                        print(f'Error: {text[:200]}')
            except Exception as e:
                print(f'Exception: {str(e)}')

if __name__ == '__main__':
    asyncio.run(test())
