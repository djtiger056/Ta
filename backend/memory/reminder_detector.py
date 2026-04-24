"""
待办事项意图检测模块
使用正则表达式和LLM检测用户的提醒/待办事项意图，并提取相关信息
"""

import json
import re
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from backend.utils.datetime_utils import get_now

# 尝试使用 zoneinfo，如果不可用则使用 pytz 或本地时间
try:
    from zoneinfo import ZoneInfo
    HAS_ZONEINFO = True
except ImportError:
    try:
        import pytz
        HAS_ZONEINFO = False
    except ImportError:
        HAS_ZONEINFO = False


def get_timezone(tz_name: Optional[str] = None):
    """获取时区对象"""
    if not tz_name:
        return None
    try:
        if HAS_ZONEINFO:
            return ZoneInfo(tz_name)
        else:
            # 尝试导入pytz
            try:
                import pytz
                return pytz.timezone(tz_name)
            except ImportError:
                return None
    except Exception:
        # 时区名称无效或无法加载时区
        return None


class ReminderDetector:
    """待办事项意图检测器"""
    
    def __init__(self, provider, timezone: str = "Asia/Shanghai"):
        """
        初始化检测器
        
        Args:
            provider: LLM提供商实例
            timezone: 时区
        """
        self.provider = provider
        self.timezone = get_timezone(timezone)
        
        # 时间表达式映射
        self.time_patterns = {
            # 明确时间
            "今晚": lambda now: self._get_tonight_time(now),
            "明天早上": lambda now: self._get_tomorrow_morning(now),
            "明早": lambda now: self._get_tomorrow_morning(now),
            "明天中午": lambda now: self._get_tomorrow_noon(now),
            "明天晚上": lambda now: self._get_tomorrow_evening(now),
            "明天": lambda now: self._get_tomorrow_time(now),
            "后天": lambda now: self._get_day_after_tomorrow(now),
            "下周": lambda now: self._get_next_week(now),
            "周末": lambda now: self._get_weekend(now),
            # 相对时间
            "等会": lambda now: now + timedelta(minutes=30),
            "晚点": lambda now: now + timedelta(minutes=30),
            "稍后": lambda now: now + timedelta(minutes=20),
            "马上": lambda now: now + timedelta(minutes=5),
            # 今天时间段
            "今天早上": lambda now: self._get_today_morning(now),
            "今天中午": lambda now: self._get_today_noon(now),
            "今天下午": lambda now: self._get_today_afternoon(now),
            "今天晚上": lambda now: self._get_today_evening(now),
            "今晚": lambda now: self._get_tonight_time(now),
            "中午": lambda now: self._get_today_noon(now),
            "下午": lambda now: self._get_today_afternoon(now),
        }
    
    async def detect_reminder_intent(self, message: str) -> Optional[Dict[str, Any]]:
        """
        检测消息是否包含待办事项意图
        
        Args:
            message: 用户消息
            
        Returns:
            如果检测到待办事项意图，返回包含以下字段的字典：
            - is_reminder: bool，是否为待办事项
            - content: str，待办事项内容
            - time_expression: str，时间表达式
            - trigger_time: datetime，触发时间
            - reminder_message: str，提醒消息模板
            如果没有检测到，返回None
        """
        try:
            # 首先使用正则表达式快速检测（更可靠）
            result = self._quick_detect_reminder(message)
            if result:
                trigger_time = self._calculate_trigger_time(
                    result.get("time_expression", ""),
                    result.get("time_hint", "")
                )
                if trigger_time:
                    result["trigger_time"] = trigger_time
                    return result
            
            # 如果正则检测失败，尝试使用LLM
            return await self._detect_with_llm(message)
            
        except Exception as e:
            print(f"待办事项意图检测失败: {e}")
            return None
    
    def _quick_detect_reminder(self, message: str) -> Optional[Dict[str, Any]]:
        """使用正则表达式快速检测待办事项意图"""
        message = message.strip()

        # 提醒意图关键词 - 必须包含这些词之一才认为是待办事项
        reminder_intent_keywords = r'(提醒我|记得|别忘了|叫我|喊我|记得要|别忘了要)'
        has_reminder_intent = re.search(reminder_intent_keywords, message)

        # 检测 "X分钟后" - 必须有提醒意图关键词
        match = re.search(r'(\d+)\s*分钟\s*后?', message)
        if match:
            # 必须有提醒意图关键词，否则只是普通陈述
            if not has_reminder_intent:
                return None
            minutes = int(match.group(1))
            content = self._extract_reminder_content(message)
            if content:
                return {
                    "is_reminder": True,
                    "content": content,
                    "time_expression": f"{minutes}分钟后",
                    "time_hint": f"{minutes}分钟后",
                    "reminder_message": f"提醒你：{content}"
                }

        # 检测 "X小时后" - 必须有提醒意图关键词
        match = re.search(r'(\d+)\s*小时\s*后?', message)
        if match:
            # 必须有提醒意图关键词，否则只是普通陈述
            if not has_reminder_intent:
                return None
            hours = int(match.group(1))
            content = self._extract_reminder_content(message)
            if content:
                return {
                    "is_reminder": True,
                    "content": content,
                    "time_expression": f"{hours}小时后",
                    "time_hint": f"{hours}小时后",
                    "reminder_message": f"提醒你：{content}"
                }

        # 检测 "等会/晚点/稍后" - 必须有提醒意图关键词
        match = re.search(r'(等会|晚点|稍后|一会儿|过会儿)', message)
        if match:
            # 必须有提醒意图关键词，否则只是普通陈述
            if not has_reminder_intent:
                return None
            time_expr = match.group(1)
            content = self._extract_reminder_content(message)
            if content:
                return {
                    "is_reminder": True,
                    "content": content,
                    "time_expression": time_expr,
                    "time_hint": "",
                    "reminder_message": f"提醒你：{content}"
                }
        
        # 检测 "今晚/明早" 等明确时间 - 必须同时有提醒意图关键词
        for time_expr in ["今晚", "明早", "明天早上", "明天中午", "明天晚上", "今天中午", "今天下午", "今天晚上"]:
            if time_expr in message:
                # 必须有提醒意图关键词，否则只是普通聊天
                if not has_reminder_intent:
                    continue
                content = self._extract_reminder_content(message)
                if content:
                    return {
                        "is_reminder": True,
                        "content": content,
                        "time_expression": time_expr,
                        "time_hint": "",
                        "reminder_message": f"提醒你：{content}"
                    }
        
        # 检测 "提醒我起床/吃饭/喝水/复习/考试"
        match = re.search(r'(提醒我|叫我|喊我)(起床|吃饭|喝水|复习|考试)', message)
        if match:
            action = match.group(2)
            return {
                "is_reminder": True,
                "content": action,
                "time_expression": "",
                "time_hint": "",
                "reminder_message": f"提醒你：{action}"
            }

        # 检测只有提醒意图关键词但没有具体时间的情况（如"记得提醒我"、"提醒我"）
        if has_reminder_intent:
            content = self._extract_reminder_content(message)
            if content:
                return {
                    "is_reminder": True,
                    "content": content,
                    "time_expression": "",
                    "time_hint": "",
                    "reminder_message": f"提醒你：{content}"
                }
            # 如果提取的内容为空，但有提醒意图，使用默认内容
            return {
                "is_reminder": True,
                "content": "提醒",
                "time_expression": "",
                "time_hint": "",
                "reminder_message": "提醒你"
            }

        return None
    
    def _extract_reminder_content(self, message: str) -> str:
        """提取待办事项内容"""
        content = message

        # 检查消息中是否包含"提醒我"关键词
        has_reminder_keyword = re.search(r'提醒我|叫我|喊我', message)

        if has_reminder_keyword:
            # 如果包含"提醒我"关键词，只移除前面的"记得"、"别忘了"等前缀
            content = re.sub(r'^(记得|别忘了|记得要|别忘了要)\s*', '', message)
            # 移除时间相关描述
            content = re.sub(r'\d+\s*(分钟|小时)\s*后?\s*', '', content)
            content = re.sub(r'(等会|晚点|稍后|一会儿|过会儿)\s*', '', content)
        else:
            # 如果不包含"提醒我"关键词，移除"提醒我"、"叫我"等前缀
            content = re.sub(r'^(记得|提醒我|叫我|喊我)\s*', '', message)
            # 移除时间相关描述
            content = re.sub(r'\d+\s*(分钟|小时)\s*后?\s*', '', content)
            content = re.sub(r'(等会|晚点|稍后|一会儿|过会儿)\s*', '', content)
            # 移除 "提醒我"、"叫我" 等后缀
            content = re.sub(r'(提醒我|叫我|喊我).*$', '', content)

        # 清理空白
        content = content.strip()
        return content if content else ""
    
    async def _detect_with_llm(self, message: str) -> Optional[Dict[str, Any]]:
        """使用LLM检测待办事项意图"""
        # 构建检测提示词
        prompt = self._build_detection_prompt(message)
        
        # 调用LLM进行意图检测
        response = await self.provider.chat([
            {"role": "system", "content": prompt},
            {"role": "user", "content": message}
        ])
        
        # 解析LLM响应
        result = self._parse_llm_response(response)
        
        if result and result.get("is_reminder"):
            # 计算触发时间
            trigger_time = self._calculate_trigger_time(
                result.get("time_expression", ""),
                result.get("time_hint", "")
            )
            
            if trigger_time:
                result["trigger_time"] = trigger_time
                return result
        
        return None
    
    def _build_detection_prompt(self, message: str) -> str:
        """构建意图检测提示词"""
        return """你是一个待办事项意图检测助手。请分析用户的消息，判断是否包含待办事项/提醒意图。

请返回JSON格式的结果，包含以下字段：
- is_reminder: 布尔值，true表示消息包含待办事项/提醒意图，false表示不包含
- content: 字符串，待办事项的内容（如果is_reminder为true）
- time_expression: 字符串，时间表达式，如"今晚"、"明早"、"晚点"等（如果is_reminder为true）
- time_hint: 字符串，时间提示，如"30分钟后"、"2小时后"等（如果is_reminder为true）
- reminder_message: 字符串，建议的提醒消息模板（如果is_reminder为true）

判断标准：
1. 用户明确要求在未来某个时间点提醒或通知
2. 包含时间相关词汇（今晚、明早、晚点、等会等）
3. 包含提醒相关动词（记得、提醒、别忘了、叫醒等）

示例：
输入："记得中午提醒我去取个快递"
输出：{"is_reminder": true, "content": "去取个快递", "time_expression": "中午", "time_hint": "", "reminder_message": "记得去取快递哦"}

输入："我再睡会，晚点再叫我起床吧"
输出：{"is_reminder": true, "content": "叫我起床", "time_expression": "晚点", "time_hint": "", "reminder_message": "起床了吗"}

输入："今天天气怎么样"
输出：{"is_reminder": false}

请只返回JSON，不要包含其他内容。"""
    
    def _parse_llm_response(self, response: str) -> Optional[Dict[str, Any]]:
        """解析LLM响应"""
        try:
            # 尝试提取JSON
            json_match = re.search(r'\{[^}]+\}', response, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                return json.loads(json_str)
            
            # 如果没有找到JSON，尝试直接解析
            return json.loads(response)
            
        except json.JSONDecodeError as e:
            print(f"解析LLM响应失败: {e}, 响应内容: {response}")
            return None
    
    def _calculate_trigger_time(self, time_expression: str, time_hint: str = "") -> Optional[datetime]:
        """
        计算触发时间
        
        Args:
            time_expression: 时间表达式
            time_hint: 时间提示
            
        Returns:
            触发时间，如果无法计算则返回None
        """
        # 获取当前时间（使用北京时间）
        now = get_now()
        
        # 先尝试匹配时间表达式
        for pattern, time_func in self.time_patterns.items():
            if pattern in time_expression:
                return time_func(now)
        
        # 如果有time_hint，尝试解析
        if time_hint:
            return self._parse_time_hint(time_hint, now)
        
        # 如果没有匹配到，默认30分钟后
        return now + timedelta(minutes=30)
    
    def _parse_time_hint(self, time_hint: str, now: datetime) -> Optional[datetime]:
        """解析时间提示"""
        try:
            # 匹配 "X分钟后"
            match = re.search(r'(\d+)\s*分钟后', time_hint)
            if match:
                minutes = int(match.group(1))
                return now + timedelta(minutes=minutes)
            
            # 匹配 "X小时后"
            match = re.search(r'(\d+)\s*小时后', time_hint)
            if match:
                hours = int(match.group(1))
                return now + timedelta(hours=hours)
            
            # 匹配 "X天后"
            match = re.search(r'(\d+)\s*天后', time_hint)
            if match:
                days = int(match.group(1))
                return now + timedelta(days=days)
            
        except Exception as e:
            print(f"解析时间提示失败: {e}")
        
        return None
    
    # 时间计算辅助方法
    
    def _get_tonight_time(self, now: datetime) -> datetime:
        """获取今晚的时间（20:00）"""
        return now.replace(hour=20, minute=0, second=0, microsecond=0)
    
    def _get_tomorrow_morning(self, now: datetime) -> datetime:
        """获取明天早上的时间（08:00）"""
        tomorrow = now + timedelta(days=1)
        return tomorrow.replace(hour=8, minute=0, second=0, microsecond=0)
    
    def _get_tomorrow_noon(self, now: datetime) -> datetime:
        """获取明天中午的时间（12:00）"""
        tomorrow = now + timedelta(days=1)
        return tomorrow.replace(hour=12, minute=0, second=0, microsecond=0)
    
    def _get_tomorrow_evening(self, now: datetime) -> datetime:
        """获取明天晚上的时间（19:00）"""
        tomorrow = now + timedelta(days=1)
        return tomorrow.replace(hour=19, minute=0, second=0, microsecond=0)
    
    def _get_tomorrow_time(self, now: datetime) -> datetime:
        """获取明天的时间（10:00）"""
        tomorrow = now + timedelta(days=1)
        return tomorrow.replace(hour=10, minute=0, second=0, microsecond=0)
    
    def _get_day_after_tomorrow(self, now: datetime) -> datetime:
        """获取后天的时间（10:00）"""
        day_after = now + timedelta(days=2)
        return day_after.replace(hour=10, minute=0, second=0, microsecond=0)
    
    def _get_next_week(self, now: datetime) -> datetime:
        """获取下周的时间（周一10:00）"""
        days_until_monday = (7 - now.weekday()) % 7 or 7
        next_monday = now + timedelta(days=days_until_monday)
        return next_monday.replace(hour=10, minute=0, second=0, microsecond=0)
    
    def _get_weekend(self, now: datetime) -> datetime:
        """获取周末的时间（周六10:00）"""
        days_until_saturday = (5 - now.weekday()) % 7
        if days_until_saturday == 0:
            days_until_saturday = 7
        next_saturday = now + timedelta(days=days_until_saturday)
        return next_saturday.replace(hour=10, minute=0, second=0, microsecond=0)
    
    def _get_today_morning(self, now: datetime) -> datetime:
        """获取今天早上的时间（如果已过，则明天早上）"""
        morning = now.replace(hour=8, minute=0, second=0, microsecond=0)
        if morning <= now:
            return morning + timedelta(days=1)
        return morning
    
    def _get_today_noon(self, now: datetime) -> datetime:
        """获取今天中午的时间（如果已过，则明天中午）"""
        noon = now.replace(hour=12, minute=0, second=0, microsecond=0)
        if noon <= now:
            return noon + timedelta(days=1)
        return noon
    
    def _get_today_afternoon(self, now: datetime) -> datetime:
        """获取今天下午的时间（15:00）"""
        afternoon = now.replace(hour=15, minute=0, second=0, microsecond=0)
        if afternoon <= now:
            return afternoon + timedelta(days=1)
        return afternoon
    
    def _get_today_evening(self, now: datetime) -> datetime:
        """获取今天晚上的时间（19:00）"""
        evening = now.replace(hour=19, minute=0, second=0, microsecond=0)
        if evening <= now:
            return evening + timedelta(days=1)
        return evening
