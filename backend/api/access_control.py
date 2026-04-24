"""用户访问控制 API 接口"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional
from ..config import config

router = APIRouter(prefix="/api", tags=["access_control"])


class AccessControlConfig(BaseModel):
    """访问控制配置模型"""
    enabled: bool = Field(description="是否启用访问控制")
    mode: str = Field(description="模式: whitelist(白名单), blacklist(黑名单), disabled(关闭)")
    whitelist: List[str] = Field(default_factory=list, description="白名单用户ID列表")
    blacklist: List[str] = Field(default_factory=list, description="黑名单用户ID列表")
    deny_message: str = Field(default="抱歉，你没有权限使用此机器人。", description="拒绝消息")


class AddUserRequest(BaseModel):
    """添加用户请求模型"""
    user_id: str = Field(description="用户ID")
    list_type: str = Field(description="列表类型: whitelist 或 blacklist")


class RemoveUserRequest(BaseModel):
    """移除用户请求模型"""
    user_id: str = Field(description="用户ID")
    list_type: str = Field(description="列表类型: whitelist 或 blacklist")


@router.get("/access-control", response_model=AccessControlConfig)
async def get_access_control():
    """获取访问控制配置"""
    return AccessControlConfig(**config.qq_access_control_config)


@router.put("/access-control", response_model=AccessControlConfig)
async def update_access_control(config_data: AccessControlConfig):
    """更新访问控制配置"""
    # 验证模式
    valid_modes = ['disabled', 'whitelist', 'blacklist']
    if config_data.mode not in valid_modes:
        raise HTTPException(
            status_code=400,
            detail=f"无效的模式。有效模式: {', '.join(valid_modes)}"
        )
    
    # 更新配置
    config.update_config('adapters', {
        'qq': {
            'access_control': config_data.model_dump()
        }
    })
    
    # 刷新配置
    config.refresh_from_file()
    
    return AccessControlConfig(**config.qq_access_control_config)


@router.post("/access-control/user")
async def add_user_to_list(request: AddUserRequest):
    """添加用户到白名单或黑名单"""
    # 验证列表类型
    if request.list_type not in ['whitelist', 'blacklist']:
        raise HTTPException(
            status_code=400,
            detail="list_type 必须是 'whitelist' 或 'blacklist'"
        )
    
    # 获取当前配置
    current_config = config.qq_access_control_config
    user_list = current_config.get(request.list_type, [])
    
    # 检查用户是否已存在
    if request.user_id in user_list:
        raise HTTPException(
            status_code=400,
            detail=f"用户 {request.user_id} 已存在于 {request.list_type} 中"
        )
    
    # 添加用户
    user_list.append(request.user_id)
    
    # 更新配置
    config.update_config('adapters', {
        'qq': {
            'access_control': {
                **current_config,
                request.list_type: user_list
            }
        }
    })
    
    # 刷新配置
    config.refresh_from_file()
    
    return {
        "message": f"用户 {request.user_id} 已添加到 {request.list_type}",
        "user_id": request.user_id,
        "list_type": request.list_type
    }


@router.delete("/access-control/user")
async def remove_user_from_list(request: RemoveUserRequest):
    """从白名单或黑名单中移除用户"""
    # 验证列表类型
    if request.list_type not in ['whitelist', 'blacklist']:
        raise HTTPException(
            status_code=400,
            detail="list_type 必须是 'whitelist' 或 'blacklist'"
        )
    
    # 获取当前配置
    current_config = config.qq_access_control_config
    user_list = current_config.get(request.list_type, [])
    
    # 检查用户是否存在
    if request.user_id not in user_list:
        raise HTTPException(
            status_code=404,
            detail=f"用户 {request.user_id} 不存在于 {request.list_type} 中"
        )
    
    # 移除用户
    user_list.remove(request.user_id)
    
    # 更新配置
    config.update_config('adapters', {
        'qq': {
            'access_control': {
                **current_config,
                request.list_type: user_list
            }
        }
    })
    
    # 刷新配置
    config.refresh_from_file()
    
    return {
        "message": f"用户 {request.user_id} 已从 {request.list_type} 中移除",
        "user_id": request.user_id,
        "list_type": request.list_type
    }


@router.get("/access-control/users")
async def get_users_in_list(list_type: str):
    """获取白名单或黑名单中的用户列表"""
    # 验证列表类型
    if list_type not in ['whitelist', 'blacklist']:
        raise HTTPException(
            status_code=400,
            detail="list_type 必须是 'whitelist' 或 'blacklist'"
        )
    
    # 获取当前配置
    current_config = config.qq_access_control_config
    user_list = current_config.get(list_type, [])
    
    return {
        "list_type": list_type,
        "users": user_list,
        "count": len(user_list)
    }