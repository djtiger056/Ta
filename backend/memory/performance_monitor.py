"""
记忆系统性能监控模块
"""

import time
import logging
from functools import wraps
from typing import Dict, Any, List
from collections import deque
from datetime import datetime
from backend.utils.datetime_utils import get_now

logger = logging.getLogger(__name__)

class PerformanceMonitor:
    """性能监控器"""
    
    def __init__(self, max_history: int = 1000):
        """
        初始化性能监控器
        
        Args:
            max_history: 最大历史记录数
        """
        self.max_history = max_history
        self.metrics: Dict[str, deque] = {
            'add_short_term_memory': deque(maxlen=max_history),
            'get_short_term_memories': deque(maxlen=max_history),
            'add_long_term_memory': deque(maxlen=max_history),
            'search_long_term_memories': deque(maxlen=max_history),
            'get_long_term_memories': deque(maxlen=max_history),
            'generate_summary': deque(maxlen=max_history),
            'cleanup_old_memories': deque(maxlen=max_history),
        }
    
    def record(self, operation: str, duration: float, success: bool = True, error: str = None):
        """
        记录性能指标
        
        Args:
            operation: 操作名称
            duration: 执行时间（秒）
            success: 是否成功
            error: 错误信息（如果有）
        """
        if operation not in self.metrics:
            self.metrics[operation] = deque(maxlen=self.max_history)
        
        self.metrics[operation].append({
            'timestamp': get_now().isoformat(),
            'duration': duration,
            'success': success,
            'error': error
        })
    
    def get_stats(self, operation: str = None) -> Dict[str, Any]:
        """
        获取性能统计
        
        Args:
            operation: 操作名称（可选，不提供则返回所有操作的统计）
            
        Returns:
            统计信息字典
        """
        if operation:
            return self._get_operation_stats(operation)
        else:
            return {op: self._get_operation_stats(op) for op in self.metrics}
    
    def _get_operation_stats(self, operation: str) -> Dict[str, Any]:
        """获取单个操作的统计信息"""
        if operation not in self.metrics or not self.metrics[operation]:
            return {
                'count': 0,
                'avg_duration': 0,
                'min_duration': 0,
                'max_duration': 0,
                'success_rate': 0,
                'error_count': 0
            }
        
        records = list(self.metrics[operation])
        durations = [r['duration'] for r in records]
        errors = [r for r in records if not r['success']]
        
        return {
            'count': len(records),
            'avg_duration': sum(durations) / len(durations) if durations else 0,
            'min_duration': min(durations) if durations else 0,
            'max_duration': max(durations) if durations else 0,
            'success_rate': (len(records) - len(errors)) / len(records) if records else 0,
            'error_count': len(errors),
            'last_errors': [r['error'] for r in errors[-5:] if r['error']]
        }
    
    def clear(self, operation: str = None):
        """清除性能记录"""
        if operation:
            if operation in self.metrics:
                self.metrics[operation].clear()
        else:
            for op in self.metrics:
                self.metrics[op].clear()


# 全局性能监控器实例
_global_monitor: PerformanceMonitor = None

def get_performance_monitor() -> PerformanceMonitor:
    """获取全局性能监控器实例"""
    global _global_monitor
    if _global_monitor is None:
        _global_monitor = PerformanceMonitor()
    return _global_monitor


def monitor_performance(operation: str):
    """
    性能监控装饰器
    
    Args:
        operation: 操作名称
    """
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            error = None
            success = True
            
            try:
                result = await func(*args, **kwargs)
                return result
            except Exception as e:
                success = False
                error = str(e)
                logger.error(f"操作 {operation} 失败: {e}", exc_info=True)
                raise
            finally:
                duration = time.time() - start_time
                monitor = get_performance_monitor()
                monitor.record(operation, duration, success, error)
                
                # 记录慢查询（超过1秒）
                if duration > 1.0:
                    logger.warning(f"慢操作 {operation}: {duration:.2f}s")
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()
            error = None
            success = True
            
            try:
                result = func(*args, **kwargs)
                return result
            except Exception as e:
                success = False
                error = str(e)
                logger.error(f"操作 {operation} 失败: {e}", exc_info=True)
                raise
            finally:
                duration = time.time() - start_time
                monitor = get_performance_monitor()
                monitor.record(operation, duration, success, error)
                
                # 记录慢查询（超过1秒）
                if duration > 1.0:
                    logger.warning(f"慢操作 {operation}: {duration:.2f}s")
        
        # 根据函数类型返回对应的包装器
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator