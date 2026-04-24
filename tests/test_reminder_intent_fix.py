"""测试待办事项意图检测修复 - 只有在用户明确要求提醒时才触发"""
import pytest
import asyncio
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.memory.reminder_detector import ReminderDetector
from backend.providers import get_provider
from backend.config import config


class MockProvider:
    """模拟LLM提供商"""
    async def chat(self, messages):
        # 返回一个不包含待办事项的响应
        return '{"is_reminder": false}'


@pytest.mark.asyncio
async def test_reminder_intent_requirement():
    """测试只有在用户明确要求提醒时才创建待办事项"""
    detector = ReminderDetector(MockProvider(), timezone="Asia/Shanghai")

    # 测试用例：不包含提醒意图关键词的消息
    test_cases_should_not_trigger = [
        "1分钟后左右我去洗漱一下",  # 用户的消息
        "30分钟后我去吃饭",
        "2小时后我要去上课",
        "等会我要去洗澡",
        "晚点我去买点东西",
        "稍后我会给你打电话",
        "今晚我有事",
        "明早我要去跑步",
        "明天中午我要开会",
    ]

    # 测试用例：包含提醒意图关键词的消息
    test_cases_should_trigger = [
        "1分钟后左右提醒我去洗漱一下",
        "记得30分钟后提醒我去吃饭",
        "别忘了2小时后提醒我去上课",
        "等会提醒我要去洗澡",
        "晚点提醒我去买点东西",
        "稍后提醒我会给你打电话",
        "今晚提醒我有事",
        "明早提醒我要去跑步",
        "明天中午提醒我要开会",
        "提醒我起床",
        "叫我吃饭",
        "喊我喝水",
    ]

    print("\n=== 测试不应该触发待办事项的消息 ===")
    for message in test_cases_should_not_trigger:
        result = await detector.detect_reminder_intent(message)
        print(f"消息: {message}")
        print(f"  结果: {result}")
        assert result is None, f"消息 '{message}' 不应该触发待办事项，但返回了: {result}"
        print("  ✓ 正确：未触发待办事项\n")

    print("\n=== 测试应该触发待办事项的消息 ===")
    for message in test_cases_should_trigger:
        result = await detector.detect_reminder_intent(message)
        print(f"消息: {message}")
        print(f"  结果: {result}")
        assert result is not None, f"消息 '{message}' 应该触发待办事项，但返回了 None"
        assert result.get("is_reminder") is True, f"消息 '{message}' 的 is_reminder 应该为 True"
        print(f"  ✓ 正确：触发了待办事项\n")

    print("\n✅ 所有测试通过！")


@pytest.mark.asyncio
async def test_edge_cases():
    """测试边界情况"""
    detector = ReminderDetector(MockProvider(), timezone="Asia/Shanghai")

    # 测试边界情况
    edge_cases = [
        ("1分钟后提醒我去洗漱一下吧", True),  # 有提醒关键词
        ("1分钟后我去洗漱一下吧", False),  # 没有提醒关键词
        ("记得提醒我", True),  # 只有提醒关键词，没有具体内容
        ("提醒我", True),  # 只有提醒关键词
        ("我去洗漱一下", False),  # 没有时间和提醒关键词
        ("今晚记得提醒我吃药", True),  # 明确时间 + 提醒关键词
        ("今晚我要吃药", False),  # 明确时间但没有提醒关键词
    ]

    print("\n=== 测试边界情况 ===")
    for message, should_trigger in edge_cases:
        result = await detector.detect_reminder_intent(message)
        print(f"消息: {message}")
        print(f"  期望: {'触发' if should_trigger else '不触发'}")
        print(f"  结果: {result}")

        if should_trigger:
            assert result is not None, f"消息 '{message}' 应该触发待办事项"
            assert result.get("is_reminder") is True, f"消息 '{message}' 的 is_reminder 应该为 True"
            print("  ✓ 正确：触发了待办事项\n")
        else:
            assert result is None, f"消息 '{message}' 不应该触发待办事项，但返回了: {result}"
            print("  ✓ 正确：未触发待办事项\n")

    print("\n✅ 边界情况测试通过！")


if __name__ == "__main__":
    asyncio.run(test_reminder_intent_requirement())
    asyncio.run(test_edge_cases())