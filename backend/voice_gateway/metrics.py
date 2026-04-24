"""语音网关基础指标统计。"""

from collections import defaultdict
from typing import Dict


class VoiceGatewayMetrics:
    """内存态指标计数器。"""

    def __init__(self):
        self._counters: Dict[str, int] = defaultdict(int)

    def inc(self, key: str, value: int = 1) -> None:
        self._counters[key] += value

    def snapshot(self) -> Dict[str, int]:
        return dict(self._counters)

