from __future__ import annotations

import os
from typing import Optional


def require_api_key(env_name: str, label: Optional[str] = None) -> str:
    """读取测试用 API Key。

    运行脚本时若未设置环境变量则退出；在 pytest 下则跳过。
    """
    key = os.getenv(env_name, "").strip()
    if key:
        return key

    message = f"请先设置环境变量 {env_name}"
    if label:
        message = f"{label}: {message}"

    try:
        import pytest

        pytest.skip(message)
    except Exception:
        raise SystemExit(message)
