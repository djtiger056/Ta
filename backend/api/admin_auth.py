"""管理员认证依赖（用于多用户配置管理）

说明：此项目支持“机器人面向多用户使用”，但配置管理应由管理员统一下发，避免每个用户都要登录后台。
"""

from __future__ import annotations

from typing import Optional

from fastapi import Depends, Header, HTTPException, Query, status

from backend.api.deps import get_access_token
from backend.config import config


def _get_admin_api_key() -> str:
    admin_cfg = config.get("admin", {}) or {}
    return str(admin_cfg.get("api_key") or "").strip()


def require_admin(
    bearer_token: str = Depends(get_access_token),
    x_admin_token: Optional[str] = Header(default=None, alias="X-Admin-Token"),
    admin_token: Optional[str] = Query(default=None),
) -> None:
    """校验管理员令牌。

    支持以下方式（任意一种即可）：
    - Header: `X-Admin-Token: <token>`
    - Query: `?admin_token=<token>`
    - Header: `Authorization: Bearer <token>`（复用 get_access_token）
    """
    expected = _get_admin_api_key()
    if not expected:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="未配置管理员密钥，请在 config.yaml 的 admin.api_key 设置后重试",
        )

    provided = (x_admin_token or admin_token or bearer_token or "").strip()
    if not provided or provided != expected:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="管理员认证失败",
        )

