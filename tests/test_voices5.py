import asyncio
import aiohttp
import json
import re
from tests._secrets import require_api_key

async def test():
    api_key = require_api_key("QHAIGC_API_KEY", "语音模型列表测试")
    headers = {'Authorization': api_key}

    async with aiohttp.ClientSession() as session:
        async with session.get('https://api.qhaigc.net/v1/models', headers=headers) as resp:
            result = await resp.json()
            models = result.get('data', [])
            voices = []
            for model in models:
                model_id = model.get('id', '')
                # 解析 qhai-tts:角色名 格式
                if model_id.startswith('qhai-tts:'):
                    voice_name = model_id.split(':', 1)[1] if ':' in model_id else model_id
                    description = model.get('description', '')
                    voices.append({
                        'name': voice_name,
                        'description': description
                    })

            print(f'Total voices found: {len(voices)}')
            print('\nVoice list:')
            for i, voice in enumerate(voices, 1):
                print(f'{i}. {voice["name"]}')

if __name__ == '__main__':
    asyncio.run(test())
