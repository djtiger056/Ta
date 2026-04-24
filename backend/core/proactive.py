import asyncio
import random
from dataclasses import dataclass, field
from datetime import datetime, time, timedelta
from typing import Any, Dict, Optional, Callable, List, Tuple, Union
from zoneinfo import ZoneInfo

from ..config import config


@dataclass
class WindowState:
    scheduled_time: Optional[datetime] = None
    scheduled_date: Optional[datetime] = None
    sent_today: int = 0
    last_sent: Optional[datetime] = None


@dataclass
class ProactiveTargetState:
    last_sent: Optional[datetime] = None
    windows: Dict[str, WindowState] = field(default_factory=dict)
    images_sent_today: int = 0
    image_quota_date: Optional[datetime] = None


class ProactiveChatScheduler:
    """主动聊天调度器，按照配置定期触发 Bot 主动问候。"""

    def __init__(self, bot):
        self.bot = bot
        self.running = False
        self.task: Optional[asyncio.Task] = None
        self.loop: Optional[asyncio.AbstractEventLoop] = None
        # 发送器可接受文本或携带图片的 payload
        self.senders: Dict[str, Callable[[Dict[str, Any], Union[str, Dict[str, Any]]], asyncio.Future]] = {}
        self.target_state: Dict[str, ProactiveTargetState] = {}
        self._config: Dict[str, Any] = config.proactive_chat_config or {}

    def register_sender(self, channel: str, sender: Callable[[Dict[str, Any], Union[str, Dict[str, Any]]], asyncio.Future]):
        """注册发送器（例如 QQ 私聊）。sender 接受 target dict 与文本或包含 image 的 payload。"""
        self.senders[channel] = sender

    async def start(self):
        if self.running:
            return
        self.loop = asyncio.get_running_loop()
        self.running = True
        self.task = asyncio.create_task(self._run_loop())
        print("[Proactive] 调度器已启动")

    async def stop(self):
        self.running = False
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
            self.task = None
        print("[Proactive] 调度器已停止")

    async def reload_config(self):
        self._config = config.proactive_chat_config or {}
        # 重置每日计数和随机时间
        self.target_state = {}
        print("[Proactive] 配置已重新加载")

    def run_coro_threadsafe(self, coro):
        """供其他线程调用的安全入口。"""
        if self.loop and self.loop.is_running():
            return asyncio.run_coroutine_threadsafe(coro, self.loop)
        raise RuntimeError("Scheduler loop is not running")

    async def trigger_once(self, target: Dict[str, Any], instruction_suffix: Optional[str] = None) -> str:
        """忽略窗口限制立即触发一次发送。"""
        instruction = self._build_instruction(target, None, override_instruction=instruction_suffix)
        return await self._send_proactive_message(target, instruction)

    async def _run_loop(self):
        while self.running:
            try:
                await self._tick()
            except Exception as e:
                print(f"[Proactive] 调度循环异常: {e}")
            await asyncio.sleep(self._config.get("check_interval_seconds", 60))

    async def _tick(self):
        if not self._config.get("enabled", False):
            return

        targets: List[Dict[str, Any]] = self._config.get("targets", [])
        if not targets:
            return

        tz = self._get_timezone()
        now = datetime.now(tz) if tz else datetime.now()

        # 检查待办事项
        await self._check_and_trigger_reminders(now)

        for target in targets:
            key = self._target_key(target)
            state = self.target_state.setdefault(key, ProactiveTargetState())
            windows = self._resolve_time_windows(target)
            if not windows:
                continue

            for idx, window_cfg in enumerate(windows):
                window_key = f"{key}#{idx}"
                window_state = state.windows.setdefault(window_key, WindowState())
                self._reset_window_if_needed(now, window_state)

                start_dt, end_dt = self._window_span(now, window_cfg)
                if not start_dt or not end_dt:
                    continue

                # 如果已经错过当日窗口，直接推迟到下一日
                if now >= end_dt:
                    self._schedule_next_day(start_dt, end_dt, window_cfg, window_state, now)
                    continue

                scheduled_time = self._ensure_schedule_time(now, start_dt, end_dt, window_cfg, window_state)
                if not scheduled_time:
                    continue

                max_messages = window_cfg.get("max_messages", window_cfg.get("max_messages_per_window", 1)) or 1
                if window_state.sent_today >= max_messages:
                    continue

                if start_dt <= now <= end_dt and now >= scheduled_time:
                    instruction = self._build_instruction(target, window_cfg)
                    await self._send_proactive_message(
                        target,
                        instruction,
                        state=state,
                        window_state=window_state,
                    )

    async def _send_proactive_message(
        self,
        target: Dict[str, Any],
        instruction: str,
        state: Optional[ProactiveTargetState] = None,
        window_state: Optional[WindowState] = None,
    ) -> str:
        channel = target.get("channel", "qq_private")
        sender = self.senders.get(channel)
        if sender is None:
            msg = f"[Proactive] 未找到发送器: {channel}"
            print(msg)
            return msg

        user_id = target.get("user_id") or "web_user"
        session_id = target.get("session_id") or user_id
        display_name = target.get("display_name") or ""
        # 计数器重置（按日）
        state = state or self.target_state.setdefault(self._target_key(target), ProactiveTargetState())
        self._reset_image_quota(state)

        if display_name:
            instruction = f"对方昵称：{display_name}\n{instruction}"

        reply = await self.bot.generate_proactive_reply(instruction, user_id=session_id)
        payload: Union[str, Dict[str, Any]] = reply
        try:
            payload = await self._maybe_attach_image(
                reply=reply,
                target=target,
                session_id=session_id,
                state=state
            )
        except Exception as e:
            print(f"[Proactive] 处理主动生图失败: {e}")

        # 发送
        await sender(target, payload)

        # 更新状态
        now = datetime.now(self._get_timezone()) if self._get_timezone() else datetime.now()
        state.last_sent = now
        if window_state:
            window_state.last_sent = now
            window_state.sent_today += 1

        return reply

    def _build_instruction(
        self,
        target: Dict[str, Any],
        window_cfg: Optional[Dict[str, Any]] = None,
        override_instruction: Optional[str] = None,
    ) -> str:
        instruction = override_instruction or ""
        if not instruction:
            parts: List[str] = []
            default_prompt = self._config.get(
                "default_prompt",
                "请以恋爱中的女友身份，用2-3句轻松语气主动问候“主人”的近况，结合最近对话和所有记忆，表现关心又自然。"
            )
            parts.append(default_prompt)
            if target.get("prompt"):
                parts.append(str(target["prompt"]))
            if window_cfg and window_cfg.get("prompt"):
                parts.append(str(window_cfg["prompt"]))
            instruction = "\n".join(parts)

        templates: List[str] = (
            (window_cfg.get("message_templates") if window_cfg else None)
            or target.get("message_templates")
            or self._config.get("message_templates")
            or []
        )
        if templates:
            instruction = f"{instruction}\n可参考灵感：{random.choice(templates)}"

        return instruction

    def _resolve_time_windows(self, target: Dict[str, Any]) -> List[Dict[str, Any]]:
        """兼容多时间段配置，支持旧 daily_window 结构"""
        if target.get("time_windows"):
            return target["time_windows"]

        daily_cfg = target.get("daily_window") or self._config.get("daily_window")
        if daily_cfg and daily_cfg.get("enabled", False):
            return [{
                "start": daily_cfg.get("start", "09:00"),
                "end": daily_cfg.get("end", "11:00"),
                "max_messages": daily_cfg.get("max_messages_per_window", 1),
                "randomize": daily_cfg.get("randomize", True),
                "prompt": daily_cfg.get("prompt"),
            }]
        return []

    def _reset_window_if_needed(self, now: datetime, window_state: WindowState):
        if window_state.scheduled_date is None:
            window_state.scheduled_date = now
            window_state.sent_today = 0
            window_state.scheduled_time = None
            return
        if window_state.scheduled_date.date() != now.date():
            window_state.sent_today = 0
            window_state.scheduled_time = None
            window_state.scheduled_date = now

    def _ensure_schedule_time(
        self,
        now: datetime,
        start_dt: datetime,
        end_dt: datetime,
        window_cfg: Dict[str, Any],
        window_state: WindowState
    ) -> Optional[datetime]:
        # 如果已有排程但跨日或落在窗口前，重算
        if window_state.scheduled_time is None or (window_state.scheduled_date and window_state.scheduled_date.date() != now.date()):
            window_state.scheduled_time = None

        if window_state.scheduled_time is None:
            if window_cfg.get("randomize", True):
                base_start = start_dt if now < start_dt else now
                total_seconds = max(1, int((end_dt - base_start).total_seconds()))
                random_seconds = random.randint(0, total_seconds)
                window_state.scheduled_time = base_start + timedelta(seconds=random_seconds)
            else:
                window_state.scheduled_time = start_dt if now < start_dt else now
            window_state.scheduled_date = now

        # 若排程早于窗口开始，则向前对齐
        if window_state.scheduled_time < start_dt:
            window_state.scheduled_time = start_dt
        return window_state.scheduled_time

    def _schedule_next_day(
        self,
        start_dt: datetime,
        end_dt: datetime,
        window_cfg: Dict[str, Any],
        window_state: WindowState,
        now: datetime,
    ):
        next_start = start_dt + timedelta(days=1)
        next_end = end_dt + timedelta(days=1)
        if window_cfg.get("randomize", True):
            total_seconds = max(1, int((next_end - next_start).total_seconds()))
            rand_seconds = random.randint(0, total_seconds)
            window_state.scheduled_time = next_start + timedelta(seconds=rand_seconds)
        else:
            window_state.scheduled_time = next_start
        window_state.scheduled_date = now

    def _window_span(self, now: datetime, window_cfg: Dict[str, Any]) -> Tuple[Optional[datetime], Optional[datetime]]:
        start_str = window_cfg.get("start")
        end_str = window_cfg.get("end")
        if not start_str or not end_str:
            return None, None
        try:
            start_t = time.fromisoformat(start_str)
            end_t = time.fromisoformat(end_str)
        except ValueError:
            return None, None

        start_dt = datetime.combine(now.date(), start_t, tzinfo=now.tzinfo)
        end_dt = datetime.combine(now.date(), end_t, tzinfo=now.tzinfo)
        if end_dt <= start_dt:
            end_dt += timedelta(days=1)
        return start_dt, end_dt

    def _get_timezone(self) -> Optional[ZoneInfo]:
        tz_name = self._config.get("timezone")
        if not tz_name:
            return None
        try:
            return ZoneInfo(tz_name)
        except Exception:
            return None

    def _target_key(self, target: Dict[str, Any]) -> str:
        return f"{target.get('channel', '')}:{target.get('user_id', '')}:{target.get('session_id', '')}"

    def _reset_image_quota(self, state: ProactiveTargetState):
        """按日重置生图计数"""
        now = datetime.now(self._get_timezone()) if self._get_timezone() else datetime.now()
        if state.image_quota_date is None or state.image_quota_date.date() != now.date():
            state.images_sent_today = 0
            state.image_quota_date = now

    def _get_image_generation_settings(self, target: Dict[str, Any]) -> Dict[str, Any]:
        """提取全局+用户级主动生图配置"""
        base_cfg = self._config.get("image_generation", {}) or {}
        target_cfg = target.get("image_generation") or {}
        enabled = target_cfg.get("enabled", base_cfg.get("enabled", False))
        max_per_day = target_cfg.get("max_per_day", base_cfg.get("max_per_day", 3))
        try:
            max_per_day = int(max_per_day) if max_per_day is not None else 0
        except (ValueError, TypeError):
            max_per_day = 0
        return {
            "enabled": bool(enabled),
            "max_per_day": max(0, max_per_day),
        }

    def _extract_image_prompt(self, reply: str) -> Tuple[str, Optional[str]]:
        """解析主动回复中的 [GEN_IMG: ...] 标签"""
        from .gen_img_parser import extract_gen_img_prompt
        return extract_gen_img_prompt(reply)

    async def _maybe_attach_image(
        self,
        reply: str,
        target: Dict[str, Any],
        session_id: str,
        state: ProactiveTargetState
    ) -> Union[str, Dict[str, Any]]:
        """根据配置和回复内容，决定是否触发生图并返回 payload
        
        优化：先发送文字，然后异步生成图片，图片生成成功后延迟发送给用户
        """
        settings = self._get_image_generation_settings(target)
        cleaned_reply, prompt = self._extract_image_prompt(reply)

        # 若未启用或无提示词，仅返回文本（去掉标签）
        if (
            not settings["enabled"]
            or not prompt
            or not self.bot
            or not getattr(self.bot, "image_gen_manager", None)
            or settings["max_per_day"] <= 0
        ):
            return cleaned_reply or reply

        # 超出配额直接返回文本
        if state.images_sent_today >= settings["max_per_day"] > 0:
            print("[Proactive] 已达到当日主动生图上限，发送纯文本")
            return cleaned_reply or reply

        # 更新计数（立即更新，避免重复触发）
        state.images_sent_today += 1
        
        # 启动后台任务异步生成图片
        asyncio.create_task(self._send_image_later(
            target=target,
            prompt=prompt,
            session_id=session_id
        ))
        
        # 立即返回文本，不等待图片生成
        return cleaned_reply or reply
    
    async def _send_image_later(
        self,
        target: Dict[str, Any],
        prompt: str,
        session_id: str
    ):
        """异步生成图片并延迟发送给用户"""
        try:
            print(f"[Proactive] 开始异步生成图片: {prompt}")
            
            # 生成图片
            image_bytes = await self.bot.generate_image(prompt, user_id=session_id)
            
            if not image_bytes:
                print("[Proactive] 主动生图失败，跳过发送图片")
                return
            
            # 延迟发送图片（延迟2秒，让用户先看到文字）
            await asyncio.sleep(2)
            
            # 获取对应的 sender
            channel = target.get("channel", "qq_private")
            sender = self.senders.get(channel)
            
            if sender is None:
                print(f"[Proactive] 未找到发送器: {channel}，无法发送图片")
                return
            
            # 发送图片
            await sender(target, {"image": image_bytes})
            print("[Proactive] 图片已延迟发送成功")
            
        except Exception as e:
            print(f"[Proactive] 异步发送图片失败: {e}")

    async def _check_and_trigger_reminders(self, now: datetime):
        """检查并触发待办事项"""
        if not self.bot or not hasattr(self.bot, 'memory_manager'):
            return

        memory_manager = self.bot.memory_manager
        if not memory_manager:
            return

        try:
            # 获取待处理的待办事项
            pending_reminders = await memory_manager.get_pending_reminders(now)

            for reminder in pending_reminders:
                user_id = reminder.get("user_id")
                session_id = reminder.get("session_id")
                content = reminder.get("content")
                reminder_message = reminder.get("reminder_message") or content
                reminder_id = reminder.get("id")

                # 查找对应的target
                target = self._find_target_for_user(user_id, session_id)
                if not target:
                    print(f"[Proactive] 未找到用户 {user_id} 的目标配置，跳过待办事项")
                    continue

                # 构建提醒指令
                instruction = f"请提醒用户：{reminder_message}\n\n这是用户之前设置的待办事项，请用自然、关心的语气提醒用户。"

                # 发送提醒消息
                try:
                    await self._send_proactive_message(target, instruction)
                    print(f"[Proactive] 已发送待办事项提醒: {content}")

                    # 标记待办事项为已完成
                    await memory_manager.complete_reminder(reminder_id)
                except Exception as e:
                    print(f"[Proactive] 发送待办事项提醒失败: {e}")

        except Exception as e:
            print(f"[Proactive] 检查待办事项失败: {e}")

    def _find_target_for_user(self, user_id: str, session_id: str) -> Optional[Dict[str, Any]]:
        """根据用户ID查找对应的target配置"""
        targets: List[Dict[str, Any]] = self._config.get("targets", [])
        for target in targets:
            if target.get("user_id") == user_id and target.get("session_id") == session_id:
                return target
        return None

    def status_snapshot(self) -> Dict[str, Any]:
        return {
            "enabled": self._config.get("enabled", False),
            "running": self.running,
            "targets": len(self._config.get("targets", []) or []),
            "targets_state": {
                key: {
                    "last_sent": state.last_sent.isoformat() if state.last_sent else None,
                    "images_sent_today": state.images_sent_today,
                    "image_quota_date": state.image_quota_date.isoformat() if state.image_quota_date else None,
                    "windows": {
                        w_key: {
                            "scheduled_time": ws.scheduled_time.isoformat() if ws.scheduled_time else None,
                            "sent_today": ws.sent_today,
                            "last_sent": ws.last_sent.isoformat() if ws.last_sent else None,
                        }
                        for w_key, ws in state.windows.items()
                    },
                }
                for key, state in self.target_state.items()
            },
        }
