"""查看 LLM_TRACE 日志中最近一次（或最近N次）请求。"""
##启用说明：你现在可以这样启动（PowerShell）：

#   $env:LLM_TRACE="1"
#   $env:LLM_TRACE_STDOUT="1"   # 可选
#   python run.py

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List


def _default_trace_dir() -> Path:
    project_root = Path(__file__).resolve().parents[1]
    return project_root / "backend" / "data" / "llm_payloads"


def _load_lines(trace_dir: Path) -> List[Dict[str, Any]]:
    if not trace_dir.exists():
        return []

    files = sorted(trace_dir.glob("*.log"), key=lambda p: p.name)
    records: List[Dict[str, Any]] = []
    for path in files:
        try:
            text = path.read_text(encoding="utf-8")
        except Exception:
            continue
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except Exception:
                continue
    return records


def _fmt_ts(raw: str) -> str:
    try:
        return datetime.fromisoformat(raw).strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return raw or "-"


def _print_record(record: Dict[str, Any], index: int) -> None:
    ts = _fmt_ts(str(record.get("ts") or ""))
    provider = record.get("provider")
    model = record.get("model")
    msg_count = record.get("message_count")
    extra = record.get("extra") or {}

    print(f"\n===== 请求 #{index} =====")
    print(f"时间: {ts}")
    print(f"provider: {provider} | model: {model} | message_count: {msg_count} | extra: {extra}")

    messages = record.get("messages") or []
    for i, message in enumerate(messages, start=1):
        role = message.get("role", "")
        content = str(message.get("content", "") or "")
        print(f"\n[{i}] role={role}")
        print(content)


def main() -> None:
    parser = argparse.ArgumentParser(description="Inspect LLM payload traces")
    parser.add_argument("--dir", default=str(_default_trace_dir()), help="trace directory")
    parser.add_argument("--last", type=int, default=1, help="show last N requests")
    parser.add_argument("--stream", choices=["true", "false", "all"], default="all", help="filter by extra.stream")
    args = parser.parse_args()

    trace_dir = Path(args.dir)
    records = _load_lines(trace_dir)
    if not records:
        print(f"未找到日志：{trace_dir}")
        return

    if args.stream != "all":
        want = args.stream == "true"
        records = [r for r in records if bool((r.get("extra") or {}).get("stream")) == want]

    if not records:
        print("过滤后无记录")
        return

    last_n = max(1, int(args.last))
    selected = records[-last_n:]
    for idx, rec in enumerate(selected, start=1):
        _print_record(rec, idx)


if __name__ == "__main__":
    main()

