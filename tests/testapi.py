import requests
import json
from tests._secrets import require_api_key
from typing import Optional, Dict, Any
import time


def check_api_connectivity(
    url: str,
    api_key: Optional[str] = None,
    method: str = "GET",
    headers: Optional[Dict[str, str]] = None,
    params: Optional[Dict[str, Any]] = None,
    data: Optional[Dict[str, Any]] = None,
    timeout: int = 10,
    verify_ssl: bool = True
) -> Dict[str, Any]:
    """
    检测API连通性

    Args:
        url: API地址
        api_key: API密钥
        method: HTTP方法 (GET, POST, PUT, DELETE)
        headers: 额外的请求头
        params: URL参数
        data: 请求体数据
        timeout: 超时时间(秒)
        verify_ssl: 是否验证SSL证书

    Returns:
        包含检测结果的字典
    """
    result = {
        "url": url,
        "success": False,
        "status_code": None,
        "response_time": None,
        "error": None,
        "response_data": None
    }

    # 构建请求头
    request_headers = {
        "Content-Type": "application/json",
        "User-Agent": "API-Connectivity-Checker/1.0"
    }

    if api_key:
        request_headers["Authorization"] = f"Bearer {api_key}"

    if headers:
        request_headers.update(headers)

    try:
        start_time = time.time()

        # 发送请求
        response = requests.request(
            method=method.upper(),
            url=url,
            headers=request_headers,
            params=params,
            json=data,
            timeout=timeout,
            verify=verify_ssl
        )

        end_time = time.time()
        result["response_time"] = round((end_time - start_time) * 1000, 2)  # 毫秒
        result["status_code"] = response.status_code

        # 判断请求是否成功
        if response.status_code < 400:
            result["success"] = True

        # 尝试解析响应数据
        try:
            result["response_data"] = response.json()
        except:
            result["response_data"] = response.text[:500]  # 限制长度

    except requests.exceptions.Timeout:
        result["error"] = f"请求超时 (超过 {timeout} 秒)"
    except requests.exceptions.ConnectionError as e:
        result["error"] = f"连接错误: {str(e)}"
    except requests.exceptions.SSLError as e:
        result["error"] = f"SSL错误: {str(e)}"
    except requests.exceptions.RequestException as e:
        result["error"] = f"请求异常: {str(e)}"
    except Exception as e:
        result["error"] = f"未知错误: {str(e)}"

    return result


def print_result(result: Dict[str, Any]) -> None:
    """打印检测结果"""
    print("=" * 60)
    print(f"API连通性检测结果")
    print("=" * 60)
    print(f"URL: {result['url']}")
    print(f"状态: {'成功' if result['success'] else '失败'}")
    print(f"状态码: {result['status_code']}")
    print(f"响应时间: {result['response_time']} ms")

    if result['error']:
        print(f"错误: {result['error']}")

    if result['response_data']:
        print(f"响应数据: {json.dumps(result['response_data'], ensure_ascii=False, indent=2)}")

    print("=" * 60)


def main():
    """主函数 - 示例用法"""
    # 配置API信息
    API_URL = "https://agentrouter.org/v1"  # 替换为你的API地址
    API_KEY = require_api_key("AGENTROUTER_API_KEY", "AgentRouter 连通性测试")  # 替换为你的API密钥

    print("开始检测API连通性...\n")

    # 检测API
    result = check_api_connectivity(
        url="https://agentrouter.org/",
        api_key=API_KEY,
        method="GET",
        timeout=10
    )

    # 打印结果
    print_result(result)

    # 根据结果执行后续操作
    if result["success"]:
        print("\n[成功] API连接正常，可以正常使用")
    else:
        print("\n[失败] API连接异常，请检查网络或API配置")


if __name__ == "__main__":
    main()
