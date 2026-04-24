import json
import os
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from threading import Lock
from typing import Any, Dict, List, Optional
from backend.utils.datetime_utils import get_now

# 默认关闭，设置 LLM_TRACE=1 时开启落盘
_TRACE_ENABLED = os.getenv("LLM_TRACE", "0").lower() not in {"0", "false", "no", "off", ""}
# 可选：设置 LLM_TRACE_STDOUT=1 时将记录同时打印到控制台
_TRACE_STDOUT = os.getenv("LLM_TRACE_STDOUT", "0").lower() not in {"0", "false", "no", "off", ""}
_lock = Lock()


def _trace_dir() -> Path:
    root = Path(__file__).resolve().parents[1]
    trace_dir = root / "data" / "llm_payloads"
    trace_dir.mkdir(parents=True, exist_ok=True)
    return trace_dir


def record_payload(provider: str, model: str, messages: List[Dict[str, Any]], extra: Optional[Dict[str, Any]] = None):
    """落盘最终发送给 LLM 的 messages，便于审计"""
    if not _TRACE_ENABLED:
        return

    payload = {
        "ts": get_now().isoformat(),
        "provider": provider,
        "model": model,
        "message_count": len(messages),
        "messages": deepcopy(messages),
    }
    if extra:
        payload["extra"] = extra

    line = json.dumps(payload, ensure_ascii=False)
    trace_path = _trace_dir() / f"{get_now():%Y%m%d}.log"
    with _lock:
        with trace_path.open("a", encoding="utf-8") as f:
            f.write(line + "\n")

    if _TRACE_STDOUT:
        print(f"[LLM_TRACE] {line}")
