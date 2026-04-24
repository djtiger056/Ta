"""FastAPI 依赖项（通用）

注意：项目要求使用 UTF-8 编码保存文件。
"""

from __future__ import annotations

from typing import Optional

from fastapi import Header, Query


def get_access_token(
    authorization: Optional[str] = Header(default=None),
    token: Optional[str] = Query(default=None),
) -> str:
    """从 Authorization: Bearer 或 query `token` 中获取访问令牌。

    兼容历史用法（query token）与前端常见用法（Bearer Token）。
    """
    if token:
        return token

    if not authorization:
        return ""

    parts = authorization.strip().split(" ", 1)
    if len(parts) == 2 and parts[0].lower() == "bearer" and parts[1].strip():
        return parts[1].strip()

    return ""

