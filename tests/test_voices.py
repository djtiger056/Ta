import asyncio
import aiohttp
import json
from tests._secrets import require_api_key

async def test():
    api_key = require_api_key("QHAIGC_API_KEY", "语音模型列表测试")
    headers = {'Authorization': api_key}

    async with aiohttp.ClientSession() as session:
        async with session.get('https://api.qhaigc.net/v1/voice/models/list', headers=headers) as resp:
            print(f'Status: {resp.status}')
            data = await resp.json()
            print(f'Voice count: {len(data.get("voice_characters", []))}')
            print(json.dumps(data, ensure_ascii=False, indent=2))

if __name__ == '__main__':
    asyncio.run(test())
