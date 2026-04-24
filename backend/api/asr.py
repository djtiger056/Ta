import logging
from pathlib import Path
from typing import Any, Dict, Optional

import yaml
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.asr.config import ASRConfig
from backend.asr.manager import ASRManager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["asr"])

_asr_manager: Optional[ASRManager] = None


class ASRConfigRequest(BaseModel):
    """ASR 配置请求体"""

    enabled: Optional[bool] = Field(None, description="是否开启语音识别")
    provider: Optional[str] = Field(None, description="ASR 提供商")
    siliconflow: Optional[Dict[str, Any]] = Field(None, description="硅基流动配置")
    qwen: Optional[Dict[str, Any]] = Field(None, description="千问配置")
    auto_send_to_llm: Optional[bool] = Field(None, description="是否自动把识别结果发给 LLM")
    processing_message: Optional[str] = Field(None, description="处理中的提示语")
    error_message: Optional[str] = Field(None, description="失败提示语")


def _get_asr_manager() -> ASRManager:
    """获取（或初始化）ASR 管理器实例"""
    global _asr_manager
    if _asr_manager is None:
        config_path = Path("config.yaml")
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config_data = yaml.safe_load(f) or {}
            asr_config = ASRConfig(**(config_data.get("asr") or {}))
        except Exception as exc:  # pragma: no cover - 仅日志记录
            logger.error("加载 ASR 配置失败，使用默认配置: %s", exc)
            asr_config = ASRConfig()
        _asr_manager = ASRManager(asr_config)
    return _asr_manager


def _deep_update(target: Dict[str, Any], source: Dict[str, Any]):
    """递归合并配置字典，避免整体覆盖嵌套字段"""
    for key, value in source.items():
        if isinstance(value, dict) and isinstance(target.get(key), dict):
            _deep_update(target[key], value)
        else:
            target[key] = value


@router.get("/asr/config")
async def get_asr_config():
    """获取 ASR 配置"""
    try:
        manager = _get_asr_manager()
        return {"success": True, "data": manager.config.dict()}
    except Exception as exc:
        logger.error("获取 ASR 配置失败: %s", exc)
        raise HTTPException(status_code=500, detail=f"获取 ASR 配置失败: {exc}")


@router.post("/asr/config")
async def update_asr_config(config_request: ASRConfigRequest):
    """更新 ASR 配置并保存到文件"""
    try:
        config_path = Path("config.yaml")
        with open(config_path, "r", encoding="utf-8") as f:
            config_data = yaml.safe_load(f) or {}

        if "asr" not in config_data or config_data["asr"] is None:
            config_data["asr"] = {}

        update_data = config_request.dict(exclude_unset=True)
        _deep_update(config_data["asr"], update_data)

        with open(config_path, "w", encoding="utf-8") as f:
            yaml.dump(config_data, f, default_flow_style=False, allow_unicode=True)

        manager = _get_asr_manager()
        manager.update_config(ASRConfig(**config_data["asr"]))

        return {"success": True, "message": "ASR 配置更新成功"}
    except Exception as exc:
        logger.error("更新 ASR 配置失败: %s", exc)
        raise HTTPException(status_code=500, detail=f"更新 ASR 配置失败: {exc}")


@router.post("/asr/test")
async def test_asr_connection():
    """测试 ASR 连接有效性"""
    try:
        manager = _get_asr_manager()
        success = await manager.test_connection()
        return {
            "success": success,
            "message": "ASR 连接正常" if success else "ASR 连接测试失败",
        }
    except Exception as exc:
        logger.error("ASR 连接测试失败: %s", exc)
        return {"success": False, "message": f"ASR 连接测试失败: {exc}"}
