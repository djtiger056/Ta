import requests
import json
from tests._secrets import require_api_key

def test_openai_endpoint():
    """测试 /openai/v1/chat/completions 端点"""

    api_key = require_api_key("AGENTROUTER_API_KEY", "AgentRouter OpenAI 端点测试")

    print("=" * 60)
    print("测试 /openai/v1/chat/completions 端点")
    print("=" * 60)

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

    print("\n[请求] https://agentrouter.org/openai/v1/chat/completions")
    print("-" * 60)

    try:
        response = requests.post(
            "https://agentrouter.org/openai/v1/chat/completions",
            headers=headers,
            json=data,
            timeout=10
        )

        print(f"状态码: {response.status_code}")
        print(f"Content-Type: {response.headers.get('Content-Type', '未知')}")
        print(f"响应长度: {len(response.text)} 字符")

        # 显示原始响应
        print(f"\n原始响应内容:")
        print(response.text)

        # 尝试解析 JSON
        try:
            result = response.json()
            print(f"\n[JSON解析成功]")
            print(json.dumps(result, indent=2, ensure_ascii=False))

            # 提取回复
            if 'choices' in result and len(result['choices']) > 0:
                reply = result['choices'][0]['message']['content']
                print(f"\n[回复] {reply}")
        except json.JSONDecodeError as e:
            print(f"\n[JSON解析失败] {str(e)}")
            print("响应不是有效的 JSON 格式，可能是 HTML 或其他格式")

    except Exception as e:
        print(f"[错误] {str(e)}")

    print("\n" + "=" * 60)

if __name__ == "__main__":
    test_openai_endpoint()
