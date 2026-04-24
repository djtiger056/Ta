"""
待办事项定时任务调度器
定期检查待办事项并发送提醒
"""

import asyncio
from datetime import datetime
from typing import Callable, Optional
import logging

logger = logging.getLogger(__name__)


class ReminderScheduler:
    """待办事项定时任务调度器"""

    def __init__(self, check_interval_seconds: int = 60):
        """
        初始化调度器

        Args:
            check_interval_seconds: 检查间隔（秒），默认60秒
        """
        self.check_interval_seconds = check_interval_seconds
        self.is_running = False
        self.task: Optional[asyncio.Task] = None
        self.memory_manager = None
        self.reminder_callback: Optional[Callable] = None

    def set_memory_manager(self, memory_manager):
        """设置记忆管理器"""
        self.memory_manager = memory_manager

    def set_reminder_callback(self, callback: Callable):
        """
        设置提醒回调函数

        Args:
            callback: 回调函数，接收参数 (reminder_data)
        """
        self.reminder_callback = callback

    async def start(self):
        """启动调度器"""
        if self.is_running:
            logger.warning("调度器已在运行")
            return

        if self.memory_manager is None:
            logger.error("未设置记忆管理器，无法启动调度器")
            return

        self.is_running = True
        self.task = asyncio.create_task(self._run_scheduler())
        logger.info("待办事项调度器已启动")

    async def stop(self):
        """停止调度器"""
        if not self.is_running:
            return

        self.is_running = False
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass

        logger.info("待办事项调度器已停止")

    async def _run_scheduler(self):
        """运行调度器主循环"""
        while self.is_running:
            try:
                await self._check_and_send_reminders()
            except Exception as e:
                logger.error(f"检查待办事项失败: {e}", exc_info=True)

            # 等待下一次检查
            await asyncio.sleep(self.check_interval_seconds)

    async def _check_and_send_reminders(self):
        """检查并发送待办事项提醒"""
        if self.memory_manager is None:
            return

        try:
            # 获取所有待处理的待办事项
            pending_reminders = await self.memory_manager.get_pending_reminders()

            if not pending_reminders:
                return

            logger.info(f"发现 {len(pending_reminders)} 个待处理的待办事项")

            # 处理每个待办事项
            for reminder in pending_reminders:
                try:
                    # 调用回调函数发送提醒
                    if self.reminder_callback:
                        await self.reminder_callback(reminder)

                    # 标记为已完成
                    reminder_id = reminder.get("id")
                    if reminder_id:
                        await self.memory_manager.complete_reminder(reminder_id)
                        logger.info(f"已发送提醒并标记为完成: {reminder.get('content')}")

                except Exception as e:
                    logger.error(f"处理待办事项失败: {e}", exc_info=True)

        except Exception as e:
            logger.error(f"获取待办事项失败: {e}", exc_info=True)

    async def check_once(self):
        """手动检查一次待办事项"""
        await self._check_and_send_reminders()