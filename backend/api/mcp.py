import json
from dataclasses import asdict
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, validator

from .chat import get_bot
from backend.mcp.daily_habits import DailyHabitsPlugin

router = APIRouter(prefix="/api/mcp", tags=["mcp"])


class InstallPluginRequest(BaseModel):
    name: str
    pip_spec: str
    module: str
    class_name: str = "Plugin"
    description: Optional[str] = ""
    auto_context: bool = False
    meta: Dict[str, Any] = Field(default_factory=dict)


class ExecuteToolRequest(BaseModel):
    tool: str
    params: Dict[str, Any] = Field(default_factory=dict)


class HabitSlot(BaseModel):
    start: str
    end: str
    activity: str
    desc: Optional[str] = ""

    @validator("start", "end")
    def _validate_time(cls, v: str) -> str:
        try:
            # 尝试标准格式
            datetime.strptime(v, "%H:%M")
            return v
        except Exception:
            pass
        # 尝试灵活解析：允许单数字小时和分钟
        parts = v.split(":")
        if len(parts) != 2:
            raise ValueError("时间格式需为 HH:MM 或 H:MM")
        hour_str, minute_str = parts
        # 补零
        if len(hour_str) == 1:
            hour_str = "0" + hour_str
        if len(minute_str) == 1:
            minute_str = "0" + minute_str
        normalized = f"{hour_str}:{minute_str}"
        # 验证是否有效
        try:
            datetime.strptime(normalized, "%H:%M")
        except Exception:
            raise ValueError("时间格式需为 HH:MM 或 H:MM")
        print(f"[HabitSlot] 时间格式化: {v} -> {normalized}")
        return normalized


class OverrideConfig(BaseModel):
    enabled: bool = False
    activity: Optional[str] = ""
    desc: Optional[str] = ""
    expires_at: Optional[str] = None


class DailyHabitsConfigRequest(BaseModel):
    enabled: bool = True
    timezone: Optional[str] = None
    default_schedule: str = "weekday"
    weekend_schedule: Optional[str] = "weekend"
    override: OverrideConfig = Field(default_factory=OverrideConfig)
    schedules: Dict[str, List[HabitSlot]] = Field(default_factory=dict)

    @validator("schedules")
    def _ensure_schedule(cls, v: Dict[str, List[HabitSlot]]) -> Dict[str, List[HabitSlot]]:
        # 允许前端空提交，后端会自动填充默认模板
        return v or {}


@router.get("/plugins")
async def list_plugins():
    """列出已加载的 MCP 插件及工具"""
    try:
        bot = get_bot()
        plugins = bot.mcp_manager.list_plugins()
        return {"plugins": plugins}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取插件列表失败: {str(e)}")


@router.post("/plugins/install")
async def install_plugin(request: InstallPluginRequest):
    """通过 pip 安装并注册一个 MCP 插件"""
    bot = get_bot()
    try:
        spec = bot.mcp_manager.install_plugin(
            name=request.name,
            pip_spec=request.pip_spec,
            module=request.module,
            class_name=request.class_name,
            description=request.description or "",
            auto_context=request.auto_context,
            meta=request.meta,
        )
        return {
            "installed": request.name,
            "spec": asdict(spec),
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"安装插件失败: {str(e)}")


@router.post("/plugins/{plugin_name}/execute")
async def execute_tool(plugin_name: str, request: ExecuteToolRequest):
    """执行 MCP 插件暴露的工具"""
    bot = get_bot()
    try:
        result = await bot.run_mcp_tool(plugin_name, request.tool, request.params)
        return {"result": result}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"执行插件失败: {str(e)}")


# 日常作息（daily_habits）相关 API
HABITS_CONFIG_PATH = DailyHabitsPlugin.default_config_path()


def _load_habits_config() -> Dict[str, Any]:
    return DailyHabitsPlugin.load_config_from_disk(HABITS_CONFIG_PATH)


def _save_habits_config(config_data: Dict[str, Any]):
    DailyHabitsPlugin.save_config(config_data, HABITS_CONFIG_PATH)
    try:
        bot = get_bot()
        plugin = getattr(bot.mcp_manager, "_plugins", {}).get("daily_habits")
        if plugin and hasattr(plugin, "invalidate_cache"):
            plugin.invalidate_cache()
    except Exception:
        # 不影响接口返回
        pass


@router.get("/daily-habits/config")
async def get_daily_habits_config():
    """获取日常作息配置"""
    try:
        return {"config": _load_habits_config()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取日常作息配置失败: {str(e)}")


@router.post("/daily-habits/config")
async def update_daily_habits_config(config_req: DailyHabitsConfigRequest):
    """更新日常作息配置（热更新，无需重启）"""
    try:
        config_data = json.loads(config_req.model_dump_json(ensure_ascii=False))
        if not config_data.get("schedules"):
            # 如果前端提交为空，自动填充默认模板以避免 400
            config_data["schedules"] = DailyHabitsPlugin._default_config().get("schedules", {})
            config_data.setdefault("default_schedule", "weekday")
            config_data.setdefault("weekend_schedule", "weekend")
        _save_habits_config(config_data)
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"保存日常作息配置失败: {str(e)}")


@router.get("/daily-habits/status")
async def get_daily_habits_status():
    """查询当前日常作息状态"""
    bot = get_bot()
    plugin = getattr(bot.mcp_manager, "_plugins", {}).get("daily_habits")
    if not plugin:
        raise HTTPException(status_code=404, detail="daily_habits 插件未加载")
    try:
        return plugin.get_status()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取状态失败: {str(e)}")
