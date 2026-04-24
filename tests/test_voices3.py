import asyncio
import aiohttp
import json
from tests._secrets import require_api_key

async def test():
    api_key = require_api_key("QHAIGC_API_KEY", "语音模型列表测试")
    headers = {'Authorization': api_key}

    # 根据API文档，尝试正确的路径
    # 文档说：GET https://api.qhaigc.net/v1/voice/models/list
    # 但测试返回404，可能需要不同的格式

    endpoints = [
        'https://api.qhaigc.net/v1/voice/models/list',
        'https://api.qhaigc.net/voice/models/list',
        'https://api.qhaigc.net/v1/audio/voices',
        'https://api.qhaigc.net/audio/voices',
        'https://api.qhaigc.net/v1/models',
    ]

    async with aiohttp.ClientSession() as session:
        for endpoint in endpoints:
            try:
                print(f'\n=== Testing: {endpoint} ===')
                async with session.get(endpoint, headers=headers) as resp:
                    print(f'Status: {resp.status}')
                    text = await resp.text()
                    print(f'Response: {text[:500]}')
                    if resp.status == 200:
                        data = json.loads(text)
                        print(f'Success! Data keys: {list(data.keys())}')
                        if 'voice_characters' in data:
                            print(f'Voice count: {len(data["voice_characters"])}')
                        break
            except Exception as e:
                print(f'Exception: {str(e)}')

if __name__ == '__main__':
    asyncio.run(test())
