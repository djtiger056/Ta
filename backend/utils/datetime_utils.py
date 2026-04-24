"""
时间工具模块
统一处理项目中所有时间相关的操作，确保使用北京时间（Asia/Shanghai）
"""

from datetime import datetime, timezone, timedelta
from typing import Optional
from zoneinfo import ZoneInfo


class DateTimeUtils:
    """时间工具类，统一处理时间操作"""
    
    # 默认时区：北京时间
    DEFAULT_TIMEZONE = "Asia/Shanghai"
    
    # 时区对象缓存
    _timezone_cache = {}
    
    @classmethod
    def get_timezone(cls, tz_name: Optional[str] = None) -> ZoneInfo:
        """
        获取时区对象
        
        Args:
            tz_name: 时区名称，默认为 Asia/Shanghai
            
        Returns:
            ZoneInfo 时区对象
        """
        tz_name = tz_name or cls.DEFAULT_TIMEZONE
        
        if tz_name not in cls._timezone_cache:
            cls._timezone_cache[tz_name] = ZoneInfo(tz_name)
        
        return cls._timezone_cache[tz_name]
    
    @classmethod
    def now(cls, tz_name: Optional[str] = None) -> datetime:
        """
        获取当前时间（带时区）
        
        Args:
            tz_name: 时区名称，默认为 Asia/Shanghai
            
        Returns:
            带时区的 datetime 对象
        """
        tz = cls.get_timezone(tz_name)
        return datetime.now(tz)
    
    @classmethod
    def now_isoformat(cls, tz_name: Optional[str] = None) -> str:
        """
        获取当前时间的 ISO 格式字符串
        
        Args:
            tz_name: 时区名称，默认为 Asia/Shanghai
            
        Returns:
            ISO 格式的时间字符串
        """
        return cls.now(tz_name).isoformat()
    
    @classmethod
    def now_timestamp(cls, tz_name: Optional[str] = None) -> float:
        """
        获取当前时间戳
        
        Args:
            tz_name: 时区名称，默认为 Asia/Shanghai
            
        Returns:
            时间戳（秒）
        """
        return cls.now(tz_name).timestamp()
    
    @classmethod
    def from_isoformat(cls, iso_string: str, tz_name: Optional[str] = None) -> datetime:
        """
        从 ISO 格式字符串解析时间
        
        Args:
            iso_string: ISO 格式的时间字符串
            tz_name: 时区名称，如果字符串中不包含时区信息，则使用此时区
            
        Returns:
            带时区的 datetime 对象
        """
        dt = datetime.fromisoformat(iso_string)
        
        # 如果解析出的时间没有时区信息，添加默认时区
        if dt.tzinfo is None:
            tz = cls.get_timezone(tz_name)
            dt = dt.replace(tzinfo=tz)
        
        return dt
    
    @classmethod
    def to_isoformat(cls, dt: datetime) -> str:
        """
        将 datetime 转换为 ISO 格式字符串
        
        Args:
            dt: datetime 对象
            
        Returns:
            ISO 格式的时间字符串
        """
        # 如果没有时区信息，添加默认时区
        if dt.tzinfo is None:
            tz = cls.get_timezone()
            dt = dt.replace(tzinfo=tz)
        
        return dt.isoformat()
    
    @classmethod
    def format_datetime(cls, dt: datetime, format_str: str = "%Y/%m/%d %H:%M:%S") -> str:
        """
        格式化时间为字符串
        
        Args:
            dt: datetime 对象
            format_str: 格式字符串，默认为 "%Y/%m/%d %H:%M:%S"
            
        Returns:
            格式化后的时间字符串
        """
        # 如果没有时区信息，添加默认时区
        if dt.tzinfo is None:
            tz = cls.get_timezone()
            dt = dt.replace(tzinfo=tz)
        
        return dt.strftime(format_str)
    
    @classmethod
    def parse_datetime(cls, time_str: str, format_str: str = "%Y/%m/%d %H:%M:%S", 
                      tz_name: Optional[str] = None) -> datetime:
        """
        从字符串解析时间
        
        Args:
            time_str: 时间字符串
            format_str: 格式字符串，默认为 "%Y/%m/%d %H:%M:%S"
            tz_name: 时区名称，默认为 Asia/Shanghai
            
        Returns:
            带时区的 datetime 对象
        """
        dt = datetime.strptime(time_str, format_str)
        tz = cls.get_timezone(tz_name)
        return dt.replace(tzinfo=tz)
    
    @classmethod
    def ensure_timezone(cls, dt: datetime, tz_name: Optional[str] = None) -> datetime:
        """
        确保 datetime 对象带有时区信息
        
        Args:
            dt: datetime 对象
            tz_name: 时区名称，默认为 Asia/Shanghai
            
        Returns:
            带时区的 datetime 对象
        """
        # 如果有时区信息，直接返回
        if dt.tzinfo is not None:
            return dt
        
        # 如果没有时区信息，添加默认时区
        tz = cls.get_timezone(tz_name)
        return dt.replace(tzinfo=tz)
    
    @classmethod
    def get_time_delta(cls, seconds: int) -> timedelta:
        """
        获取时间差
        
        Args:
            seconds: 秒数
            
        Returns:
            timedelta 对象
        """
        return timedelta(seconds=seconds)
    
    @classmethod
    def get_date_range_today(cls, tz_name: Optional[str] = None) -> tuple[datetime, datetime]:
        """
        获取今天的起止时间
        
        Args:
            tz_name: 时区名称，默认为 Asia/Shanghai
            
        Returns:
            (开始时间, 结束时间)
        """
        now = cls.now(tz_name)
        start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_day = now.replace(hour=23, minute=59, second=59, microsecond=999999)
        return start_of_day, end_of_day


# 便捷函数
def get_now(tz_name: Optional[str] = None) -> datetime:
    """获取当前时间（带时区）"""
    return DateTimeUtils.now(tz_name)


def get_now_isoformat(tz_name: Optional[str] = None) -> str:
    """获取当前时间的 ISO 格式字符串"""
    return DateTimeUtils.now_isoformat(tz_name)


def get_now_timestamp(tz_name: Optional[str] = None) -> float:
    """获取当前时间戳"""
    return DateTimeUtils.now_timestamp(tz_name)


def from_isoformat(iso_string: str, tz_name: Optional[str] = None) -> datetime:
    """从 ISO 格式字符串解析时间"""
    return DateTimeUtils.from_isoformat(iso_string, tz_name)


def to_isoformat(dt: datetime) -> str:
    """将 datetime 转换为 ISO 格式字符串"""
    return DateTimeUtils.to_isoformat(dt)


def format_datetime(dt: datetime, format_str: str = "%Y/%m/%d %H:%M:%S") -> str:
    """格式化时间为字符串"""
    return DateTimeUtils.format_datetime(dt, format_str)


def ensure_timezone(dt: datetime, tz_name: Optional[str] = None) -> datetime:
    """确保 datetime 对象带有时区信息"""
    return DateTimeUtils.ensure_timezone(dt, tz_name)