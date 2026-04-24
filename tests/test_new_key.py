import requests
import json
from tests._secrets import require_api_key

def test_new_api_key():
    """测试新的 API Key"""

    new_api_key = require_api_key("AGENTROUTER_API_KEY", "AgentRouter 新 Key 测试")

    print("=" * 60)
    print("测试新的 API Key")
    print("=" * 60)

    headers = {
        "Authorization": f"Bearer {new_api_key}",
        "Content-Type": "application/json"
    }

    # 测试聊天 API
    chat_data = {
        "model": "gpt-3.5-turbo",
        "messages": [
            {"role": "user", "content": "测试连接"}
        ],
        "max_tokens": 10
    }

    print("\n[测试] 聊天 API")
    print("-" * 60)

    try:
        response = requests.post(
            "https://agentrouter.org/v1/chat/completions",
            headers=headers,
            json=chat_data,
            timeout=10
        )

        print(f"状态码: {response.status_code}")

        if response.status_code == 200:
            print("[成功] API 调用成功!")
            result = response.json()
            print(f"响应: {json.dumps(result, indent=2, ensure_ascii=False)}")

            # 提取回复内容
            if 'choices' in result and len(result['choices']) > 0:
                reply = result['choices'][0]['message']['content']
                print(f"\n回复内容: {reply}")
        else:
            print(f"[失败] API 调用失败")
            print(f"错误: {response.text}")

    except Exception as e:
        print(f"[错误] {str(e)}")

    # 测试获取模型列表
    print("\n[测试] 获取模型列表")
    print("-" * 60)

    try:
        response = requests.get(
            "https://agentrouter.org/v1/models",
            headers=headers,
            timeout=10
        )

        print(f"状态码: {response.status_code}")

        if response.status_code == 200:
            print("[成功] 获取模型列表成功!")
            result = response.json()
            print(f"响应: {json.dumps(result, indent=2, ensure_ascii=False)}")

            # 列出可用模型
            if 'data' in result:
                print(f"\n可用模型 ({len(result['data'])} 个):")
                for model in result['data'][:10]:  # 只显示前10个
                    print(f"  - {model['id']}")
        else:
            print(f"[失败] 获取模型列表失败")
            print(f"错误: {response.text}")

    except Exception as e:
        print(f"[错误] {str(e)}")

    print("\n" + "=" * 60)
    print("[结论]")
    print("=" * 60)

if __name__ == "__main__":
    test_new_api_key()
