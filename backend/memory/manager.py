"""
记忆管理器
管理短期记忆、中期记忆和长期记忆（使用向量存储）
"""

import asyncio
import json
import re
import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.future import select
from backend.utils.datetime_utils import get_now, to_isoformat

from .models import (
    MemoryConfig, MemoryItemDB, MemorySummaryDB,
    MemoryItem, MemorySummary, ConversationMessage, ReminderItemDB, Base
)
from .vector_store import VectorStore
from .base import BaseMemoryManager
from .external_memobase import MemobaseClient


logger = logging.getLogger(__name__)


class MemoryManager(BaseMemoryManager):
    """记忆管理器（使用向量存储）"""

    def __init__(self, config: MemoryConfig, db_url: str = None):
        """
        初始化记忆管理器

        Args:
            config: 记忆配置
            db_url: 数据库URL，默认使用SQLite
        """
        super().__init__(config, db_url)
        self.vector_store = None
        self.external_client: Optional[MemobaseClient] = None

    def _use_external_long_term(self) -> bool:
        return (self.config.long_term_strategy or "local").lower() == "external"

    def _get_external_client(self) -> Optional[MemobaseClient]:
        base_url = getattr(self.config, "external_memory_base_url", None)
        if not base_url:
            return None
        api_key = getattr(self.config, "external_memory_api_key", None)
        timeout = getattr(self.config, "external_memory_timeout", 30)
        if self.external_client is None:
            self.external_client = MemobaseClient(
                base_url=base_url,
                api_key=api_key,
                timeout=timeout,
            )
        return self.external_client

    async def initialize(self):
        """异步初始化记忆管理器"""
        try:
            # 初始化数据库（调用父类方法）
            await super()._init_database()

            # 初始化向量存储（长期记忆）
            if self.config.long_term_enabled and not self._use_external_long_term():
                await self._init_vector_store()
        except Exception as e:
            # 初始化失败，重置状态
            self.engine = None
            self.async_session = None
            self.vector_store = None
            raise

    async def _init_vector_store(self):
        """初始化向量存储"""
        try:
            self.vector_store = VectorStore(
                persist_directory="./data/chroma",
                embedding_provider=self.config.embedding_provider,
                embedding_model_name=self.config.embedding_model,
                embedding_api_base=self.config.embedding_api_base,
                embedding_api_key=self.config.embedding_api_key,
                embedding_timeout=self.config.embedding_timeout,
                embedding_dimensions=self.config.embedding_dimensions,
            )
            await self.vector_store.initialize()
            logger.info("向量存储初始化成功")
        except Exception as e:
            print(f"向量存储初始化失败: {e}")
            # 不抛出异常，但记录警告
            self.vector_store = None

    # ========== 长期记忆相关方法（向量存储实现）==========

    async def _extract_important_memories(self, session_id: str, user_id: str):
        """提取重要信息到长期记忆"""
        if not self.config.long_term_enabled:
            return
        if self._use_external_long_term():
            return

        try:
            # 获取最近的对话
            recent_memories = await self.get_short_term_memories(user_id, session_id, limit=10)

            # 待办事项时间模式（用于检测用户请求）
            reminder_patterns = [
                r'记得.*\d+.*(分钟|分钟|分钟|分).*提醒',
                r'提醒.*\d+.*(分钟|分钟|分钟|分)',
                r'\d+.*分钟后.*提醒',
                r'\d+.*分钟后.*叫我',
                r'(等会|晚点|稍后).*提醒',
                r'提醒我.*(起床|吃饭|喝水|复习|考试)',
            ]

            for memory in recent_memories[-3:]:  # 只检查最近3条
                # 简化的重要性评估（实际应该用LLM评估）
                content = ""
                message = memory.get("message") or {}
                if isinstance(message, dict):
                    content = message.get("content", "") or ""
                if not content:
                    raw_content = memory.get("content", "")
                    if raw_content:
                        try:
                            parsed = json.loads(raw_content)
                            content = parsed.get("content", raw_content)
                        except Exception:
                            content = raw_content
                if not content:
                    continue

                # 跳过系统生成/冗余内容，避免污染长期记忆
                skip_markers = [
                    "CQ:image",
                    "CQ:record",
                    "[图片生成",
                    "图片生成结果",
                    "图片生成请求",
                    "[图片描述摘要",
                    "这是一个图片的描述",
                    "这是一张图片的描述",
                ]
                if any(marker in content for marker in skip_markers):
                    continue

                # 计算重要性
                importance = self._evaluate_importance(content)

                # 检查是否为待办事项请求（用户消息中包含提醒模式）
                role = message.get("role") if isinstance(message, dict) else None
                is_user_message = role == "user"

                if is_user_message:
                    # 检测用户消息是否为待办事项请求
                    is_reminder_request = any(re.search(pattern, content) for pattern in reminder_patterns)
                    if is_reminder_request:
                        # 待办事项请求的重要性降低50%，但仍可能进入长期记忆（如果还有其他重要内容）
                        importance = importance * 0.5
                        print(f"[记忆] 待办事项请求降权: {content[:30]}... (importance={importance:.2f})")

                # 检查是否为用户消息且重要性超过阈值
                if is_user_message and importance > self.config.importance_threshold:
                    # 去重：相同用户的相同内容已经存在则跳过
                    if await self._is_duplicate_long_term(user_id, content):
                        continue

                    # 添加到长期记忆
                    if self.vector_store:
                        now = get_now()
                        self.vector_store.add_texts(
                            texts=[content],
                            metadatas=[{
                                "user_id": user_id,
                                "session_id": session_id,
                                "importance": importance,
                                "source": "auto_extract",
                                "timestamp": to_isoformat(now)  # 使用北京时间
                            }],
                            ids=[f"{user_id}_{session_id}_{int(now.timestamp())}"]
                        )
        except Exception as e:
            print(f"提取重要记忆失败: {e}")

    async def _is_duplicate_long_term(self, user_id: str, content: str, threshold: float = 0.97) -> bool:
        """判断是否已有相似的长期记忆，避免重复写入"""
        try:
            existing = await self.search_long_term_memories(
                user_id=user_id,
                query=content,
                top_k=3,
                score_threshold=threshold
            )
            return len(existing) > 0
        except Exception as e:
            print(f"检查长期记忆重复失败: {e}")
            return False

    def _evaluate_importance(self, content: str) -> float:
        """
        评估记忆重要性（优化版本）

        Args:
            content: 记忆内容

        Returns:
            重要性评分（0-1）
        """
        base_score = 0.2
        bonus = 0.0
        penalty = 0.0

        # 检测临时性内容（待办事项、短期提醒等）
        temporary_patterns = [
            r'\d+\s*分钟[后左右]',
            r'\d+\s*小时[后左右]',
            r'(等会|晚点|稍后|一会儿|过会儿)',
            r'(提醒我|叫我|喊我).*?(起床|吃饭|喝水|洗漱)',
            r'今晚|明早|明天',
        ]
        if any(re.search(pattern, content) for pattern in temporary_patterns):
            penalty += 0.3  # 临时性内容大幅降权

        # 长期记忆标记（真正重要的信息）
        long_term_markers = [
            "以后",
            "下次",
            "务必",
            "希望你",
            "喜欢",
            "爱看",
            "偏好",
            "最喜欢",
        ]
        if any(marker in content for marker in long_term_markers):
            bonus += 0.5  # 长期记忆标记获得高分

        # 短期提醒标记（区别于长期记忆）
        short_term_markers = [
            "记住",
            "记得",
            "别忘",
        ]
        if any(marker in content for marker in short_term_markers):
            # 如果同时包含时间表达式，说明是短期提醒，不加分
            has_time = any(re.search(pattern, content) for pattern in temporary_patterns)
            if not has_time:
                bonus += 0.2

        # 个人偏好信息
        if re.search(r"(买|穿|口味|爱好|风格)", content):
            bonus += 0.25

        # 内容长度评分
        length = len(content)
        if length > 40:
            bonus += 0.05
        if length > 80:
            bonus += 0.05

        score = base_score + bonus - penalty
        return max(0.1, min(1.0, score))

    async def add_long_term_memory(self, user_id: str, content: str,
                                 importance: float = 0.5,
                                 metadata: Dict[str, Any] = None) -> bool:
        """
        手动添加长期记忆

        Args:
            user_id: 用户ID
            content: 记忆内容
            importance: 重要性评分
            metadata: 元数据

        Returns:
            是否成功
        """
        if not self.config.long_term_enabled:
            return False

        try:
            if self._use_external_long_term():
                client = self._get_external_client()
                if client is None:
                    return False
                await client.get_or_create_user(user_id)
                await client.insert_chat_blob(user_id, [
                    {"role": "user", "content": content}
                ])
                await client.flush(user_id, blob_type="chat", sync=False)
                return True

            if self.vector_store is None:
                return False

            now = get_now()
            memory_id = f"{user_id}_{now.timestamp()}"

            # 准备元数据
            memory_metadata = {
                "importance": importance,
                "source": "manual",
                "timestamp": to_isoformat(now)  # 使用北京时间
            }
            if metadata:
                memory_metadata.update(metadata)

            success = await self.vector_store.add_memory(
                memory_id=memory_id,
                user_id=user_id,
                content=content,
                metadata=memory_metadata
            )

            # 清理旧记忆（如果超过最大数量）
            if success:
                await self._cleanup_old_long_term_memories(user_id)

            return success
        except Exception as e:
            print(f"添加长期记忆失败: {e}")
            return False

    async def search_long_term_memories(self, user_id: str, query: str,
                                      top_k: int = None,
                                      score_threshold: float = None) -> List[Dict[str, Any]]:
        """
        搜索长期记忆

        Args:
            user_id: 用户ID
            query: 查询文本
            top_k: 返回数量（默认使用配置）
            score_threshold: 分数阈值（默认使用配置）

        Returns:
            相关记忆列表
        """
        if not self.config.long_term_enabled:
            return []

        if self._use_external_long_term():
            client = self._get_external_client()
            if client is None:
                return []
            limit = int(top_k or self.config.rag_top_k)
            events = await client.get_events(user_id=user_id, limit=limit, query=query)
            results: List[Dict[str, Any]] = []
            for event in events:
                event_data = event.get("event_data") or {}
                event_tip = event_data.get("event_tip") or ""
                profile_delta = event_data.get("profile_delta") or []
                if not event_tip and profile_delta:
                    delta_lines = []
                    for delta in profile_delta:
                        attrs = delta.get("attributes") or {}
                        topic = attrs.get("topic") or ""
                        sub_topic = attrs.get("sub_topic") or ""
                        content = delta.get("content") or ""
                        label = "::".join(filter(None, [topic, sub_topic]))
                        delta_lines.append(f"{label}: {content}" if label else content)
                    event_tip = "；".join([line for line in delta_lines if line])
                if not event_tip:
                    continue
                results.append({
                    "id": event.get("id") or "",
                    "content": event_tip,
                    "metadata": {
                        "source": "memobase_event",
                        "event_tags": event_data.get("event_tags"),
                    },
                    "similarity": 0.8,
                    "created_at": event.get("created_at"),
                })
            return results

        if self.vector_store is None:
            return []

        top_k = top_k or self.config.rag_top_k
        score_threshold = score_threshold or self.config.rag_score_threshold

        return await self.vector_store.search_memories(
            query=query,
            user_id=user_id,
            top_k=top_k,
            score_threshold=score_threshold
        )

    async def get_long_term_memories(self, user_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        """
        获取用户的长期记忆

        Args:
            user_id: 用户ID
            limit: 最大返回数量

        Returns:
            长期记忆列表
        """
        if not self.config.long_term_enabled:
            return []

        if self._use_external_long_term():
            client = self._get_external_client()
            if client is None:
                return []
            profiles = await client.get_profiles(user_id=user_id)
            results: List[Dict[str, Any]] = []
            for profile in profiles:
                topic = profile.get("topic") or ""
                sub_topic = profile.get("sub_topic") or ""
                content = profile.get("content") or ""
                label = "::".join(filter(None, [topic, sub_topic]))
                results.append({
                    "id": profile.get("id") or f"{topic}_{sub_topic}",
                    "content": f"{label}: {content}" if label else content,
                    "metadata": {
                        "source": "memobase_profile",
                        "topic": topic,
                        "sub_topic": sub_topic,
                    },
                    "importance": None,
                    "created_at": profile.get("created_at"),
                })
            return results[:limit]

        if self.vector_store is None:
            return []

        return await self.vector_store.get_user_memories(user_id, limit)

    async def _cleanup_old_long_term_memories(self, user_id: str):
        """清理旧的长期记忆（如果超过最大数量）"""
        if not self.config.long_term_enabled:
            return
        if self._use_external_long_term():
            return
        if self.vector_store is None:
            return

        try:
            memories = await self.vector_store.get_user_memories(user_id, limit=2000)

            if len(memories) > self.config.max_long_term_memories:
                # 按重要性排序，删除重要性最低的
                memories_with_importance = []
                for mem in memories:
                    importance = mem.get("metadata", {}).get("importance", 0.5)
                    memories_with_importance.append((importance, mem))

                # 按重要性升序排序
                memories_with_importance.sort(key=lambda x: x[0])

                # 计算需要删除的数量
                to_delete = len(memories) - self.config.max_long_term_memories
                for i in range(to_delete):
                    if i < len(memories_with_importance):
                        mem_id = memories_with_importance[i][1].get("id")
                        if mem_id:
                            await self.vector_store.delete_memory(mem_id)

                print(f"已清理 {to_delete} 个长期记忆")
        except Exception as e:
            print(f"清理长期记忆失败: {e}")

    # ========== 配置管理（扩展基类方法）==========

    async def update_config(self, new_config: MemoryConfig):
        """更新记忆配置"""
        super().update_config(new_config)

        # 如果启用了长期记忆但向量存储未初始化，则初始化
        if self.config.long_term_enabled and not self._use_external_long_term() and self.vector_store is None:
            await self._init_vector_store()

    async def get_stats(self) -> Dict[str, Any]:
        """获取记忆系统统计信息（扩展基类方法）"""
        stats = await super().get_stats()
        stats["vector_store_status"] = "未启用"
        stats["system_type"] = "向量记忆系统"

        # 获取向量存储统计
        if self._use_external_long_term():
            stats["system_type"] = "外部记忆系统"
            client = self._get_external_client()
            if client is None:
                stats["external_memory_status"] = {"ok": False, "reason": "未配置外部记忆服务"}
                stats["long_term_count"] = 0
            else:
                ok = await client.ping()
                stats["external_memory_status"] = {"ok": ok, "provider": self.config.external_memory_provider}
                stats["long_term_count"] = 0
        elif self.vector_store:
            vector_stats = self.vector_store.get_stats()
            stats["vector_store_status"] = vector_stats
            stats["long_term_count"] = vector_stats.get("count", 0)

        return stats

    async def add_long_term_memories_batch(self, user_id: str, memories: List[Dict[str, Any]]) -> int:
        """批量添加长期记忆（外部记忆合并为单次写入）"""
        if not self.config.long_term_enabled or not memories:
            return 0
        if self._use_external_long_term():
            client = self._get_external_client()
            if client is None:
                return 0
            await client.get_or_create_user(user_id)
            messages = []
            for mem in memories:
                content = mem.get("content") or ""
                if content:
                    messages.append({"role": "user", "content": content})
            if not messages:
                return 0
            await client.insert_chat_blob(user_id, messages)
            await client.flush(user_id, blob_type="chat", sync=False)
            return len(messages)
        return await super().batch_add_long_term_memories(user_id, memories)

    async def get_external_profiles(self, user_id: str) -> List[Dict[str, Any]]:
        if not self._use_external_long_term():
            return []
        client = self._get_external_client()
        if client is None:
            return []
        # 确保用户存在
        await client.get_or_create_user(user_id)
        return await client.get_profiles(user_id=user_id)

    async def get_external_events(self, user_id: str, limit: int = 10, query: Optional[str] = None) -> List[Dict[str, Any]]:
        if not self._use_external_long_term():
            return []
        client = self._get_external_client()
        if client is None:
            return []
        # 确保用户存在
        await client.get_or_create_user(user_id)
        return await client.get_events(user_id=user_id, limit=limit, query=query)

    async def get_external_context(self, user_id: str, max_token_size: int = 500,
                                   prefer_topics: Optional[List[str]] = None,
                                   customize_context_prompt: Optional[str] = None) -> str:
        if not self._use_external_long_term():
            return ""
        client = self._get_external_client()
        if client is None:
            return ""
        # 确保用户存在
        await client.get_or_create_user(user_id)
        return await client.get_context(
            user_id=user_id,
            max_token_size=max_token_size,
            prefer_topics=prefer_topics,
            customize_context_prompt=customize_context_prompt
        )

    async def ping_external_memory(self) -> Dict[str, Any]:
        if not self._use_external_long_term():
            return {"ok": False, "reason": "strategy_not_external"}
        client = self._get_external_client()
        if client is None:
            return {"ok": False, "reason": "missing_config"}
        ok = await client.ping()
        return {"ok": ok, "provider": self.config.external_memory_provider}

    # ========== 清除所有记忆（扩展基类方法）==========

    async def clear_all_memories(self, user_id: str, session_id: str = None):
        """清除所有记忆"""
        try:
            # 清除短期记忆和摘要（调用基类方法）
            await super().clear_short_term_memories(user_id, session_id)

            # 清除摘要
            if self.async_session:
                async with self.async_session() as session:
                    stmt = select(MemorySummaryDB).where(
                        MemorySummaryDB.user_id == user_id
                    )
                    if session_id:
                        stmt = stmt.where(MemorySummaryDB.session_id == session_id)

                    result = await session.execute(stmt)
                    summaries = result.scalars().all()

                    for summary in summaries:
                        await session.delete(summary)

                    await session.commit()

            # 清除长期记忆
            if self.vector_store:
                await self.vector_store.clear_user_memories(user_id)

            # 清除会话状态
            if session_id:
                key = f"{user_id}_{session_id}"
                if key in self.session_states:
                    del self.session_states[key]

            return True
        except Exception as e:
            print(f"清除所有记忆失败: {e}")
            return False
