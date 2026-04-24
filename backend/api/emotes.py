from fastapi import APIRouter, HTTPException
from typing import Any, Dict, Optional

from ..config import config
from ..emote import EmoteConfig, EmoteManager
from .chat import get_bot, reset_bot

router = APIRouter(prefix="/api/emotes", tags=["emotes"])

_fallback_manager: Optional[EmoteManager] = None


def _get_manager() -> EmoteManager:
    """优先复用Bot上的管理器，避免配置不一致"""
    global _fallback_manager
    try:
        bot = get_bot()
        if bot and getattr(bot, "emote_manager", None):
            return bot.emote_manager
    except Exception:
        pass

    if _fallback_manager is None:
        emote_cfg = config.emote_config if hasattr(config, "emote_config") else EmoteConfig()
        _fallback_manager = EmoteManager(emote_cfg)
    return _fallback_manager


@router.get("/config")
async def get_emote_config():
    try:
        manager = _get_manager()
        return {
            "config": manager.config.dict(),
            "categories": manager.list_categories_info(),
            "base_path": str(manager.base_path),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取表情包配置失败: {str(e)}")


@router.post("/config")
async def update_emote_config(payload: Dict[str, Any]):
    """更新表情包配置并持久化"""
    try:
        new_config = EmoteConfig(**payload)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"配置格式错误: {str(e)}")

    try:
        manager = _get_manager()
        manager.update_config(new_config)
        config.update_config("emotes", new_config.dict())
        # 触发Bot实例刷新
        reset_bot()
        return {
            "success": True,
            "config": manager.config.dict(),
            "categories": manager.list_categories_info(),
            "base_path": str(manager.base_path),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"保存表情包配置失败: {str(e)}")


@router.post("/reload")
async def reload_emote_files():
    """重新扫描表情包目录"""
    try:
        manager = _get_manager()
        manager.refresh_files()
        return {
            "success": True,
            "categories": manager.list_categories_info(),
            "base_path": str(manager.base_path),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"重载失败: {str(e)}")
