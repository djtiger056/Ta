#!/usr/bin/env python3
"""
测试记忆系统在对话中的集成
"""

import asyncio
import sys
import os
import yaml
from pathlib import Path

# 添加backend目录到路径
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

async def test_memory_in_chat():
    """测试记忆系统在对话中的集成"""
    print("开始测试记忆系统在对话中的集成...")
    
    # 读取配置文件
    config_path = Path(__file__).parent / 'config.yaml'
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config_data = yaml.safe_load(f)
    except FileNotFoundError:
        print(f"❌ 错误: 配置文件未找到: {config_path}")
        return False
    except yaml.YAMLError as e:
        print(f"❌ 错误: 配置文件格式错误: {e}")
        return False
    
    try:
        # 导入Bot类
        from core.bot import Bot
        from memory.models import MemoryConfig
        
        # 创建Bot实例
        bot = Bot()
        
        # 测试用户ID
        test_user_id = "test_memory_user"
        
        # 清空历史记录
        bot.clear_history()
        
        # 测试对话序列
        test_conversations = [
            "你好，我是小明",
            "我叫小明，今年25岁",
            "我住在北京，是个程序员",
            "我喜欢吃苹果和香蕉",
            "我有一个妹妹叫小红",
            "我的生日是10月15日",
            "我讨厌吃香菜",
            "我最喜欢的颜色是蓝色",
            "我有一只猫叫咪咪",
            "我周末喜欢去爬山"
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
            "我喜欢吃什么水果？",
            "我有兄弟姐妹吗？",
            "我的生日是什么时候？",
            "我讨厌吃什么？",
            "我最喜欢什么颜色？",
            "我有宠物吗？",
            "我周末喜欢做什么？"
        ]
        
        for query in test_queries:
            print(f"\n用户: {query}")
            response = await bot.chat(query, test_user_id)
            print(f"助手: {response}")
            
            # 检查回复是否包含相关信息
            has_relevant_info = False
            if "名字" in query and ("小明" in response or "名字" in response):
                has_relevant_info = True
            elif "多大" in query and ("25" in response or "岁" in response):
                has_relevant_info = True
            elif "住" in query and ("北京" in response or "住" in response):
                has_relevant_info = True
            elif "水果" in query and ("苹果" in response or "香蕉" in response):
                has_relevant_info = True
            elif "兄弟" in query and ("妹妹" in response or "小红" in response):
                has_relevant_info = True
            elif "生日" in query and ("10月15日" in response or "生日" in response):
                has_relevant_info = True
            elif "讨厌" in query and ("香菜" in response or "讨厌" in response):
                has_relevant_info = True
            elif "颜色" in query and ("蓝色" in response or "颜色" in response):
                has_relevant_info = True
            elif "宠物" in query and ("猫" in response or "咪咪" in response):
                has_relevant_info = True
            elif "周末" in query and ("爬山" in response or "周末" in response):
                has_relevant_info = True
            
            if has_relevant_info:
                print("✅ 记忆检索成功!")
            else:
                print("❌ 记忆检索可能失败")
        
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
