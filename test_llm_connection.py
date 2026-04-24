#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
LLM 中转站连通测试脚本
支持输入 API Key、URL、模型名进行连通性测试
"""

import asyncio
import aiohttp
import json
import time
from typing import Dict, Any


class LLMConnectionTester:
    """LLM API 连通性测试器"""

    def __init__(self, api_key: str, api_base: str, model: str):
        self.api_key = api_key
        self.api_base = self._normalize_api_base(api_base)
        self.model = model

    def _normalize_api_base(self, api_base: str) -> str:
        """确保 Base URL 格式正确"""
        normalized = api_base.strip()
        suffix = '/chat/completions'
        if normalized.endswith(suffix):
            normalized = normalized[:-len(suffix)]
        return normalized.rstrip('/')

    def _get_headers(self) -> Dict[str, str]:
        """获取请求头"""
        return {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }

    async def test_connection(self, max_tokens: int = 50, timeout: int = 30) -> Dict[str, Any]:
        """
        测试 API 连接

        Args:
            max_tokens: 最大生成 token 数
            timeout: 超时时间（秒）

        Returns:
            包含测试结果的字典
        """
        url = f"{self.api_base}/chat/completions"
        test_messages = [
            {"role": "user", "content": "你好，请回复'连接成功'来确认连接。"}
        ]

        data = {
            "model": self.model,
            "messages": test_messages,
            "temperature": 0.5,
            "max_tokens": max_tokens,
            "stream": False
        }

        result = {
            "success": False,
            "message": "",
            "response_time": 0,
            "response_content": None,
            "error": None
        }

        try:
            start_time = time.time()

            timeout_config = aiohttp.ClientTimeout(total=timeout)
            async with aiohttp.ClientSession(timeout=timeout_config) as session:
                async with session.post(url, headers=self._get_headers(), json=data) as response:
                    end_time = time.time()
                    result["response_time"] = round((end_time - start_time) * 1000, 2)  # 毫秒

                    if response.status == 200:
                        result["success"] = True
                        result["message"] = f"✅ 连接成功 (HTTP {response.status})"
                        result_data = await response.json()
                        result["response_content"] = result_data

                        # 提取回复内容
                        if 'choices' in result_data and len(result_data['choices']) > 0:
                            content = result_data['choices'][0]['message']['content']
                            result["message"] += f"\n📝 模型回复: {content}"
                    else:
                        error_text = await response.text()
                        result["message"] = f"❌ 连接失败 (HTTP {response.status})"
                        result["error"] = f"HTTP {response.status}: {error_text}"

        except aiohttp.ClientError as e:
            end_time = time.time()
            result["response_time"] = round((end_time - start_time) * 1000, 2)
            result["message"] = f"❌ 网络错误: {str(e)}"
            result["error"] = str(e)

        except asyncio.TimeoutError:
            end_time = time.time()
            result["response_time"] = round((end_time - start_time) * 1000, 2)
            result["message"] = f"❌ 请求超时（超过 {timeout} 秒）"
            result["error"] = "Timeout"

        except Exception as e:
            end_time = time.time()
            result["response_time"] = round((end_time - start_time) * 1000, 2)
            result["message"] = f"❌ 未知错误: {str(e)}"
            result["error"] = str(e)

        return result


def print_banner():
    """打印横幅"""
    print("=" * 60)
    print("          LLM 中转站连通测试工具")
    print("=" * 60)
    print()


def print_result(result: Dict[str, Any]):
    """打印测试结果"""
    print("\n" + "=" * 60)
    print("测试结果:")
    print("=" * 60)
    print(f"状态: {result['message']}")
    print(f"响应时间: {result['response_time']} ms")

    if result['success'] and result['response_content']:
        print("\n完整响应:")
        print(json.dumps(result['response_content'], ensure_ascii=False, indent=2))

    if result['error']:
        print(f"\n错误详情: {result['error']}")

    print("=" * 60)


async def main():
    """主函数"""
    print_banner()

    print("请输入 LLM API 配置信息:\n")

    # 获取用户输入
    api_key = input("🔑 API Key: ").strip()
    if not api_key:
        print("❌ API Key 不能为空！")
        return

    api_base = input("🌐 API URL (例如: https://api.openai.com/v1): ").strip()
    if not api_base:
        print("❌ API URL 不能为空！")
        return

    model = input("🤖 模型名称 (例如: gpt-3.5-turbo): ").strip()
    if not model:
        print("❌ 模型名称不能为空！")
        return

    max_tokens = input("📊 最大 Token 数 (默认 50，回车使用默认值): ").strip()
    max_tokens = int(max_tokens) if max_tokens.isdigit() else 50

    timeout = input("⏱️  超时时间（秒，默认 30，回车使用默认值）: ").strip()
    timeout = int(timeout) if timeout.isdigit() else 30

    print(f"\n🔍 正在测试连接...")
    print(f"   API URL: {api_base}")
    print(f"   模型: {model}")
    print(f"   最大 Token: {max_tokens}")
    print(f"   超时: {timeout} 秒")
    print()

    # 创建测试器并执行测试
    tester = LLMConnectionTester(api_key, api_base, model)
    result = await tester.test_connection(max_tokens=max_tokens, timeout=timeout)

    # 打印结果
    print_result(result)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n❌ 测试已取消")
    except Exception as e:
        print(f"\n\n❌ 发生错误: {str(e)}")
