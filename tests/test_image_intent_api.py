"""测试主动生图API功能"""
import requests
import json

BASE_URL = "http://localhost:8002"

def test_chat_with_image_intent():
    """测试聊天接口中的主动生图功能"""
    print("=== 测试聊天接口中的主动生图功能 ===")

    # 测试1: 普通聊天（没有生图意图）
    print("\n测试1: 普通聊天")
    try:
        response = requests.post(
            f"{BASE_URL}/api/chat",
            json={"message": "你好呀", "user_id": "test_user"}
        )
        print(f"状态码: {response.status_code}")
        data = response.json()
        print(f"回复: {data.get('response')}")
        print(f"是否有图片: {'是' if data.get('image') else '否'}")
        assert response.status_code == 200, "请求失败"
        assert not data.get('image'), "普通聊天不应该返回图片"
        print("[OK] 测试通过")
    except Exception as e:
        print(f"[FAIL] 测试失败: {str(e)}")

    # 测试2: 触发生图的聊天
    # 注意：这个测试依赖于系统提示词，让AI主动输出 [GEN_IMG: ...] 标签
    print("\n测试2: 主动生图聊天（如果AI有生图意图）")
    try:
        response = requests.post(
            f"{BASE_URL}/api/chat",
            json={"message": "给我看看你今天的学习状态", "user_id": "test_user"}
        )
        print(f"状态码: {response.status_code}")
        data = response.json()
        print(f"回复: {data.get('response')}")
        print(f"是否有图片: {'是' if data.get('image') else '否'}")
        if data.get('image'):
            print(f"图片大小: {len(data['image'])} bytes")
            print("[OK] 图片生成成功")
        else:
            print("[INFO] AI没有生图意图（这是正常的，取决于系统提示词和AI的判断）")
    except Exception as e:
        print(f"[FAIL] 测试失败: {str(e)}")

    print("\n=== 测试完成 ===")


def test_stream_chat_with_image_intent():
    """测试流式聊天接口中的主动生图功能"""
    print("\n=== 测试流式聊天接口中的主动生图功能 ===")

    try:
        response = requests.post(
            f"{BASE_URL}/api/chat/stream",
            json={"message": "给我看看你今天的学习状态", "user_id": "test_user"},
            stream=True
        )

        print(f"状态码: {response.status_code}")
        full_content = ""
        has_image = False

        for line in response.iter_lines():
            if line:
                line_str = line.decode('utf-8')
                if line_str.startswith('data: '):
                    data_str = line_str[6:]  # 去掉 'data: ' 前缀
                    if data_str == '[DONE]':
                        break
                    try:
                        data = json.loads(data_str)
                        if 'content' in data:
                            full_content += data['content']
                        if 'image' in data:
                            has_image = True
                            print(f"收到图片数据，大小: {len(data['image'])} bytes")
                    except json.JSONDecodeError:
                        pass

        print(f"完整回复: {full_content}")
        print(f"是否有图片: {'是' if has_image else '否'}")
        if has_image:
            print("[OK] 流式图片生成成功")
        else:
            print("[INFO] AI没有生图意图（这是正常的）")
    except Exception as e:
        print(f"[FAIL] 测试失败: {str(e)}")

    print("\n=== 流式测试完成 ===")


if __name__ == "__main__":
    # 检查服务是否运行
    try:
        response = requests.get(f"{BASE_URL}/docs")
        print("[OK] 后端服务正在运行")
        test_chat_with_image_intent()
        test_stream_chat_with_image_intent()
    except requests.exceptions.ConnectionError:
        print("[FAIL] 后端服务未运行，请先启动后端服务")
        print("启动命令: python run.py")
    except Exception as e:
        print(f"[FAIL] 测试失败: {str(e)}")