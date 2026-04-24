import asyncio
import aiohttp
import json
from tests._secrets import require_api_key

async def test():
    api_key = require_api_key("QHAIGC_API_KEY", "语音模型列表测试")
    headers = {'Authorization': api_key}

    async with aiohttp.ClientSession() as session:
        async with session.get('https://api.qhaigc.net/v1/models', headers=headers) as resp:
            data = await resp.json()
            print(f'Total models: {len(data.get("data", []))}')

            # 查找TTS相关模型
            tts_models = [m for m in data.get('data', []) if 'tts' in m.get('id', '').lower() or 'audio' in m.get('id', '').lower() or 'voice' in m.get('id', '').lower()]
            print(f'\nTTS/Voice related models ({len(tts_models)}):')
            for model in tts_models:
                print(f"  - {model.get('id')}: {model.get('description', 'N/A')}")

            # 查找qhai-tts模型
            qhai_tts = [m for m in data.get('data', []) if 'qhai-tts' in m.get('id', '')]
            if qhai_tts:
                print(f'\nqhai-tts model details:')
                print(json.dumps(qhai_tts[0], ensure_ascii=False, indent=2))

if __name__ == '__main__':
    asyncio.run(test())
