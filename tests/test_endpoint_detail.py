import requests
import json
from tests._secrets import require_api_key

def test_endpoint_detail():
    """详细测试不同端点"""

    api_key = require_api_key("AGENTROUTER_API_KEY", "AgentRouter 端点测试")

    print("=" * 60)
    print("详细测试 API 端点")
    print("=" * 60)

    # 测试不同的端点
    endpoints = [
        {
            "name": "v1/chat/completions",
            "url": "https://agentrouter.org/v1/chat/completions"
        },
        {
            "name": "chat/completions (不带v1)",
            "url": "https://agentrouter.org/chat/completions"
        },
        {
            "name": "v1/models",
            "url": "https://agentrouter.org/v1/models"
        },
        {
            "name": "models",
            "url": "https://agentrouter.org/models"
        }
    ]

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    chat_data = {
        "model": "gpt-3.5-turbo",
        "messages": [
            {"role": "user", "content": "测试"}
        ],
        "max_tokens": 10
    }

    for endpoint in endpoints:
        print(f"\n[测试] {endpoint['name']}")
        print(f"URL: {endpoint['url']}")
        print("-" * 60)

        try:
            # 对于 models 端点使用 GET，其他使用 POST
            if "models" in endpoint['url']:
                response = requests.get(endpoint['url'], headers=headers, timeout=10)
            else:
                response = requests.post(endpoint['url'], headers=headers, json=chat_data, timeout=10)

            print(f"状态码: {response.status_code}")
            print(f"Content-Type: {response.headers.get('Content-Type', '未知')}")

            # 尝试解析 JSON
            try:
                result = response.json()
                print(f"响应(JSON): {json.dumps(result, indent=2, ensure_ascii=False)}")
            except:
                print(f"响应(文本): {response.text[:500]}")

        except Exception as e:
            print(f"错误: {str(e)}")

    print("\n" + "=" * 60)

if __name__ == "__main__":
    test_endpoint_detail()
