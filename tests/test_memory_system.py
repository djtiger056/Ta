#!/usr/bin/env python3
"""
测试记忆系统功能
"""

import asyncio
import sys
import os
import yaml
from pathlib import Path

# 添加backend目录到路径
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

async def test_memory_system():
    """测试记忆系统功能"""
    print("开始测试记忆系统...")
    
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
    
    # 检查记忆配置
    memory_config = config_data.get('memory', {})
    if not memory_config.get('long_term_enabled'):
        print("❌ 错误: 长期记忆未启用")
        return False
    
    print(f"✅ 记忆系统配置检查通过")
    print(f"   短期记忆: {'启用' if memory_config.get('short_term_enabled') else '禁用'}")
    print(f"   中期记忆: {'启用' if memory_config.get('mid_term_enabled') else '禁用'}")
    print(f"   长期记忆: {'启用' if memory_config.get('long_term_enabled') else '禁用'}")
    print(f"   向量存储: {'启用' if memory_config.get('long_term_enabled') else '禁用'}")
    
    try:
        # 导入记忆系统
        from memory.models import MemoryConfig
        from memory.manager import MemoryManager
        
        # 创建记忆管理器
        config = MemoryConfig(**memory_config)
        memory_manager = MemoryManager(config)
        
        # 初始化记忆管理器
        print("🔄 正在初始化记忆管理器...")
        await memory_manager.initialize()
        print("✅ 记忆管理器初始化成功!")
        
        # 测试添加长期记忆
        print("🔄 正在测试添加长期记忆...")
        test_user_id = "test_user"
        test_memories = [
            "我喜欢吃苹果，特别是红苹果",
            "我的生日是5月20日",
            "我讨厌吃辣的食物",
            "我有一个宠物狗叫小白",
            "我住在上海，喜欢在黄浦江边散步"
        ]
        
        for i, memory in enumerate(test_memories):
            success = await memory_manager.add_long_term_memory(
                user_id=test_user_id,
                content=memory,
                importance=0.8
            )
            if success:
                print(f"   ✅ 添加记忆 {i+1}: {memory}")
            else:
                print(f"   ❌ 添加记忆失败: {memory}")
        
        # 测试搜索记忆
        print("🔄 正在测试搜索记忆...")
        test_queries = [
            "我喜欢什么水果?",
            "我的生日是什么时候?",
            "我住在哪里?",
            "我有宠物吗?"
        ]
        
        for query in test_queries:
            results = await memory_manager.search_long_term_memories(
                user_id=test_user_id,
                query=query,
                top_k=3
            )
            print(f"\n   查询: {query}")
            if results:
                for i, result in enumerate(results, 1):
                    print(f"   {i}. {result['content']} (相似度: {result['similarity']:.2f})")
            else:
                print("   ❌ 未找到相关记忆")
        
        # 获取统计信息
        print("\n🔄 正在获取记忆系统统计信息...")
        stats = await memory_manager.get_stats()
        print(f"   短期记忆数量: {stats.get('short_term_count', 0)}")
        print(f"   摘要数量: {stats.get('summary_count', 0)}")
        print(f"   长期记忆数量: {stats.get('long_term_count', 0)}")
        print(f"   向量存储状态: {stats.get('vector_store_status', {})}")
        
        print("\n✅ 记忆系统测试完成!")
        return True
        
    except Exception as e:
        print(f"❌ 测试过程中发生错误: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    asyncio.run(test_memory_system())
