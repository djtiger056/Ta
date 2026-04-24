"""
记忆系统优化测试
测试新增的优化功能：缓存、批量操作、过期机制等
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from backend.memory.local_manager import LocalMemoryManager
from backend.memory.models import MemoryConfig, ConversationMessage


@pytest.mark.asyncio
class TestMemoryOptimization:
    """记忆系统优化测试"""
    
    @pytest.fixture
    async def memory_manager(self):
        """创建记忆管理器实例"""
        config = MemoryConfig(
            short_term_enabled=True,
            mid_term_enabled=True,
            long_term_enabled=True,
            use_local_memory=True,
        )
        manager = LocalMemoryManager(config)
        await manager.initialize()
        yield manager
        # 清理测试数据
        await manager.clear_all_memories("test_user")
    
    @pytest.mark.asyncio
    async def test_memory_cache_hit(self, memory_manager):
        """测试缓存命中"""
        user_id = "test_user"
        session_id = "test_session"
        
        # 添加短期记忆
        message = ConversationMessage(
            role="user",
            content="这是一条测试消息"
        )
        await memory_manager.add_short_term_memory(user_id, session_id, message)
        
        # 第一次查询（缓存未命中）
        start_time = datetime.now()
        memories1 = await memory_manager.get_short_term_memories(user_id, session_id)
        first_duration = (datetime.now() - start_time).total_seconds()
        
        # 第二次查询（缓存命中）
        start_time = datetime.now()
        memories2 = await memory_manager.get_short_term_memories(user_id, session_id)
        second_duration = (datetime.now() - start_time).total_seconds()
        
        # 验证结果一致
        assert len(memories1) == len(memories2)
        assert len(memories1) == 1
        
        # 验证缓存命中后速度更快
        assert second_duration < first_duration
    
    @pytest.mark.asyncio
    async def test_memory_cache_invalidation(self, memory_manager):
        """测试缓存失效"""
        user_id = "test_user"
        session_id = "test_session"
        
        # 添加短期记忆
        message = ConversationMessage(role="user", content="消息1")
        await memory_manager.add_short_term_memory(user_id, session_id, message)
        
        # 第一次查询
        memories1 = await memory_manager.get_short_term_memories(user_id, session_id)
        assert len(memories1) == 1
        
        # 添加新记忆
        message2 = ConversationMessage(role="user", content="消息2")
        await memory_manager.add_short_term_memory(user_id, session_id, message2)
        
        # 再次查询（应该返回2条记录，缓存已失效）
        memories2 = await memory_manager.get_short_term_memories(user_id, session_id)
        assert len(memories2) == 2
    
    @pytest.mark.asyncio
    async def test_batch_add_short_term_memories(self, memory_manager):
        """测试批量添加短期记忆"""
        user_id = "test_user"
        session_id = "test_session"
        
        # 准备批量数据
        messages = [
            ConversationMessage(role="user", content=f"消息{i}")
            for i in range(10)
        ]
        
        # 批量添加
        success = await memory_manager.batch_add_short_term_memories(user_id, session_id, messages)
        assert success
        
        # 验证结果
        memories = await memory_manager.get_short_term_memories(user_id, session_id)
        assert len(memories) == 10
    
    @pytest.mark.asyncio
    async def test_batch_add_long_term_memories(self, memory_manager):
        """测试批量添加长期记忆"""
        user_id = "test_user"
        
        # 准备批量数据
        memories_data = [
            {"content": f"长期记忆{i}", "importance": 0.5 + i * 0.05}
            for i in range(10)
        ]
        
        # 批量添加
        success = await memory_manager.batch_add_long_term_memories(user_id, memories_data)
        assert success
        
        # 验证结果
        memories = await memory_manager.get_long_term_memories(user_id)
        assert len(memories) == 10
    
    @pytest.mark.asyncio
    async def test_update_long_term_memory(self, memory_manager):
        """测试更新长期记忆"""
        user_id = "test_user"
        
        # 添加记忆
        await memory_manager.add_long_term_memory(user_id, "原始内容", 0.5)
        
        # 获取记忆ID
        memories = await memory_manager.get_long_term_memories(user_id)
        memory_id = memories[0]["id"]
        
        # 更新记忆
        success = await memory_manager.update_long_term_memory(
            memory_id,
            "更新后的内容",
            0.8
        )
        assert success
        
        # 验证更新
        updated_memories = await memory_manager.get_long_term_memories(user_id)
        assert updated_memories[0]["content"] == "更新后的内容"
        assert updated_memories[0]["importance"] == 0.8


@pytest.mark.asyncio
class TestReminderScheduler:
    """待办事项调度器测试"""
    
    @pytest.fixture
    async def memory_manager(self):
        """创建记忆管理器实例"""
        config = MemoryConfig(
            short_term_enabled=True,
            long_term_enabled=True,
            use_local_memory=True
        )
        manager = LocalMemoryManager(config)
        await manager.initialize()
        yield manager
        # 清理测试数据
        await manager.clear_all_memories("test_user")
    
    @pytest.mark.asyncio
    async def test_add_reminder(self, memory_manager):
        """测试添加待办事项"""
        user_id = "test_user"
        session_id = "test_session"
        
        # 添加待办事项
        trigger_time = datetime.now() + timedelta(minutes=30)
        success = await memory_manager.add_reminder(
            user_id=user_id,
            session_id=session_id,
            content="测试待办事项",
            trigger_time=trigger_time
        )
        assert success
        
        # 验证添加成功
        reminders = await memory_manager.get_all_reminders(user_id=user_id)
        assert len(reminders) == 1
        assert reminders[0]["content"] == "测试待办事项"
    
    @pytest.mark.asyncio
    async def test_get_pending_reminders(self, memory_manager):
        """测试获取待处理待办事项"""
        user_id = "test_user"
        session_id = "test_session"
        
        # 添加一个已过期的待办事项
        past_time = datetime.now() - timedelta(minutes=10)
        await memory_manager.add_reminder(
            user_id=user_id,
            session_id=session_id,
            content="过期待办事项",
            trigger_time=past_time
        )
        
        # 添加一个未来的待办事项
        future_time = datetime.now() + timedelta(minutes=30)
        await memory_manager.add_reminder(
            user_id=user_id,
            session_id=session_id,
            content="未来待办事项",
            trigger_time=future_time
        )
        
        # 获取待处理待办事项
        pending = await memory_manager.get_pending_reminders()
        assert len(pending) == 1
        assert pending[0]["content"] == "过期待办事项"
    
    @pytest.mark.asyncio
    async def test_complete_reminder(self, memory_manager):
        """测试完成待办事项"""
        user_id = "test_user"
        session_id = "test_session"
        
        # 添加待办事项
        trigger_time = datetime.now() - timedelta(minutes=10)
        await memory_manager.add_reminder(
            user_id=user_id,
            session_id=session_id,
            content="测试待办事项",
            trigger_time=trigger_time
        )
        
        # 获取待办事项ID
        reminders = await memory_manager.get_all_reminders(user_id=user_id)
        reminder_id = reminders[0]["id"]
        
        # 完成待办事项
        success = await memory_manager.complete_reminder(reminder_id)
        assert success
        
        # 验证状态更新
        updated_reminders = await memory_manager.get_all_reminders(user_id=user_id)
        assert updated_reminders[0]["status"] == "completed"
        assert updated_reminders[0]["completed_at"] is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
