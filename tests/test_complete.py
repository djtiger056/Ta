import requests
import json
from tests._secrets import require_api_key

def test_agentrouter_complete():
    """完整测试 agentrouter 中转站"""

    api_key = require_api_key("AGENTROUTER_API_KEY", "AgentRouter 完整测试")

    print("=" * 60)
    print("完整测试 agentrouter 中转站")
    print("=" * 60)

    # 测试1: GET 请求（网站访问）
    print("\n[测试1] GET 请求网站根路径")
    print("-" * 60)

    try:
        response = requests.get("https://agentrouter.org/", timeout=10)
        print(f"状态码: {response.status_code}")
        print(f"响应类型: {response.headers.get('Content-Type', '未知')}")
        print(f"响应长度: {len(response.text)} 字符")

        if response.status_code == 200:
            print("[成功] 网站可以访问")
            # 只显示前100个字符
            print(f"响应内容(前100字符): {response.text[:100]}...")
        else:
            print(f"[失败] 状态码: {response.status_code}")
    except Exception as e:
        print(f"[错误] {str(e)}")

    # 测试2: POST 请求（聊天 API）
    print("\n[测试2] POST 请求聊天 API")
    print("-" * 60)

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    data = {
        "model": "gpt-3.5-turbo",
        "messages": [
            {"role": "user", "content": "测试连接"}
        ],
        "max_tokens": 10
    }

    test_endpoints = [
        "https://agentrouter.org/v1/chat/completions",
        "https://agentrouter.org/chat/completions",
    ]

    for endpoint in test_endpoints:
        print(f"\n测试端点: {endpoint}")

        try:
            response = requests.post(endpoint, headers=headers, json=data, timeout=10)

            print(f"  状态码: {response.status_code}")

            if response.status_code == 200:
                print(f"  [成功] API调用成功!")
                result = response.json()
                print(f"  响应: {json.dumps(result, indent=2, ensure_ascii=False)}")
            else:
                print(f"  [失败] API调用失败")
                print(f"  错误: {response.text}")

        except Exception as e:
            print(f"  [错误] {str(e)}")

    print("\n" + "=" * 60)
    print("[总结]")
    print("=" * 60)
    print("如果 GET 请求成功但 POST 请求失败，说明：")
    print("1. 网站可以正常访问")
    print("2. API Key 可能无效或未授权")
    print("3. 需要联系中转站获取正确的 API Key")
    print("\n建议:")
    print("- 检查 API Key 是否正确")
    print("- 查看 agentrouter 文档确认使用方式")
    print("- 联系客服获取授权")

if __name__ == "__main__":
    test_agentrouter_complete()
