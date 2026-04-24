import requests
import json
from tests._secrets import require_api_key

def test_alternative_methods():
    """尝试不同的认证方式和端点"""

    api_key = require_api_key("AGENTROUTER_API_KEY", "AgentRouter 认证测试")

    print("=" * 60)
    print("尝试不同的认证方式")
    print("=" * 60)

    # 测试1: 不同的 Authorization 格式
    print("\n[测试1] 不同的 Authorization 头格式")
    print("-" * 60)

    auth_formats = [
        {"name": "Bearer", "value": f"Bearer {api_key}"},
        {"name": "Raw", "value": api_key},
        {"name": "API Key", "value": f"API-Key: {api_key}"},
    ]

    for auth_format in auth_formats:
        print(f"\n尝试: {auth_format['name']}")

        headers = {
            "Authorization": auth_format['value'],
            "Content-Type": "application/json"
        }

        data = {
            "model": "gpt-3.5-turbo",
            "messages": [{"role": "user", "content": "test"}],
            "max_tokens": 10
        }

        try:
            response = requests.post(
                "https://agentrouter.org/v1/chat/completions",
                headers=headers,
                json=data,
                timeout=10
            )
            print(f"  状态码: {response.status_code}")

            if response.status_code == 200:
                print(f"  [成功] 找到正确的认证方式!")
                result = response.json()
                print(f"  响应: {result}")
                break
            else:
                print(f"  [失败] {response.text[:100]}")

        except Exception as e:
            print(f"  [错误] {str(e)}")

    # 测试2: 不同的端点
    print("\n[测试2] 不同的端点")
    print("-" * 60)

    endpoints = [
        "https://agentrouter.org/v1/chat/completions",
        "https://agentrouter.org/api/v1/chat/completions",
        "https://agentrouter.org/openai/v1/chat/completions",
        "https://agentrouter.org/api/chat/completions",
    ]

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    data = {
        "model": "gpt-3.5-turbo",
        "messages": [{"role": "user", "content": "test"}],
        "max_tokens": 10
    }

    for endpoint in endpoints:
        print(f"\n尝试: {endpoint}")

        try:
            response = requests.post(
                endpoint,
                headers=headers,
                json=data,
                timeout=10
            )
            print(f"  状态码: {response.status_code}")

            if response.status_code == 200:
                print(f"  [成功] 找到正确的端点!")
                result = response.json()
                print(f"  响应: {result}")
                break
            else:
                print(f"  [失败] {response.text[:100]}")

        except Exception as e:
            print(f"  [错误] {str(e)}")

    # 测试3: 添加额外的请求头
    print("\n[测试3] 添加额外的请求头")
    print("-" * 60)

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0",
        "Origin": "https://agentrouter.org",
        "Referer": "https://agentrouter.org/"
    }

    try:
        response = requests.post(
            "https://agentrouter.org/v1/chat/completions",
            headers=headers,
            json=data,
            timeout=10
        )
        print(f"状态码: {response.status_code}")

        if response.status_code == 200:
            print(f"[成功] 添加额外请求头后成功!")
            result = response.json()
            print(f"响应: {result}")
        else:
            print(f"[失败] {response.text}")

    except Exception as e:
        print(f"[错误] {str(e)}")

    print("\n" + "=" * 60)

if __name__ == "__main__":
    test_alternative_methods()
