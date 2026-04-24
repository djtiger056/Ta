"""测试原始问题：用户的消息"1分钟后左右我去洗漱一下"不应该触发待办事项"""
import pytest
import asyncio
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.memory.reminder_detector import ReminderDetector


class MockProvider:
    """模拟LLM提供商"""
    async def chat(self, messages):
        return '{"is_reminder": false}'


@pytest.mark.asyncio
async def test_original_issue():
    """测试原始问题：用户的消息"1分钟后左右我去洗漱一下"不应该触发待办事项"""
    detector = ReminderDetector(MockProvider(), timezone="Asia/Shanghai")

    # 原始问题消息
    message = "1分钟后左右我去洗漱一下"
    result = await detector.detect_reminder_intent(message)

    print(f"\n原始问题消息: {message}")
    print(f"检测结果: {result}")

    # 应该不触发待办事项
    assert result is None, f"消息 '{message}' 不应该触发待办事项，但返回了: {result}"
    print("[OK] 正确：未触发待办事项")

    # 对比：包含提醒意图关键词的消息应该触发
    message_with_reminder = "1分钟后左右提醒我去洗漱一下"
    result_with_reminder = await detector.detect_reminder_intent(message_with_reminder)

    print(f"\n对比消息: {message_with_reminder}")
    print(f"检测结果: {result_with_reminder}")

    # 应该触发待办事项
    assert result_with_reminder is not None, f"消息 '{message_with_reminder}' 应该触发待办事项"
    assert result_with_reminder.get("is_reminder") is True
    print("[OK] 正确：触发了待办事项")

    print("\n[SUCCESS] 原始问题已修复！")


if __name__ == "__main__":
    asyncio.run(test_original_issue())