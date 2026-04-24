import requests

try:
    response = requests.get('http://localhost:8002/api/tts/voices')
    print(f'Status: {response.status_code}')
    print(f'Response: {response.text}')
    data = response.json()
    if data.get('success'):
        voices = data.get('data', [])
        print(f'\nTotal voices: {len(voices)}')
        for i, voice in enumerate(voices[:10], 1):
            print(f'{i}. {voice.get("name")} - {voice.get("description", "")}')
except Exception as e:
    print(f'Error: {str(e)}')