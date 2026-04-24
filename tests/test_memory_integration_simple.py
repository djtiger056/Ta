#!/usr/bin/env python3
"""
测试记忆系统在对话中的集成（简化版）
"""

import asyncio
import sys
import os
from pathlib import Path

# 切换到backend目录
backend_dir = Path(__file__).parent / 'backend'
os.chdir(backend_dir)
sys.path.insert(0, str(backend_dir))

async def test_memory_in_chat():
    """测试记忆系统在对话中的集成"""
    print("开始测试记忆系统在对话中的集成...")
    
    try:
        # 导入Bot类
        from core.bot import Bot
        
        # 创建Bot实例
        bot = Bot()
        
        # 测试用户ID
        test_user_id = "test_memory_user"
        
        # 清空历史记录
        bot.clear_history()
        
        # 检查记忆管理器是否初始化
        if not bot.memory_manager:
            print("❌ 记忆管理器未初始化")
            return False
        
        print("✅ 记忆管理器已初始化")
        
        # 等待记忆管理器初始化
        await bot._ensure_memory_manager_initialized()
        
        # 测试对话序列
        test_conversations = [
            "你好，我是小明",
            "我叫小明，今年25岁",
            "我住在北京，是个程序员",
            "我喜欢吃苹果和香蕉"
        ]
        
        print("\n🔄 正在进行第一轮对话（建立记忆）...")
        for i, message in enumerate(test_conversations):
            print(f"\n用户: {message}")
            response = await bot.chat(message, test_user_id)
            print(f"助手: {response[:50]}...")
            
            # 短暂延迟，确保记忆保存
            await asyncio.sleep(0.1)
        
        # 清空当前对话历史（但保留记忆）
        bot.clear_history()
        
        print("\n\n🔄 正在进行第二轮对话（测试记忆检索）...")
        test_queries = [
            "我叫什么名字？",
            "我多大了？",
            "我住在哪里？",
            "我喜欢吃什么水果？"
        ]
        
        for query in test_queries:
            print(f"\n用户: {query}")
            response = await bot.chat(query, test_user_id)
            print(f"助手: {response}")
        
        # 获取记忆统计
        if bot.memory_manager:
            print("\n🔄 正在获取记忆系统统计信息...")
            stats = await bot.memory_manager.get_stats()
            print(f"   短期记忆数量: {stats.get('short_term_count', 0)}")
            print(f"   摘要数量: {stats.get('summary_count', 0)}")
            print(f"   长期记忆数量: {stats.get('long_term_count', 0)}")
        
        print("\n✅ 记忆系统集成测试完成!")
        return True
        
    except Exception as e:
        print(f"❌ 测试过程中发生错误: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    asyncio.run(test_memory_in_chat())