"""用户认证 API 接口"""
from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from backend.user import user_manager, auth_manager, User
from backend.api.deps import get_access_token


router = APIRouter(prefix="/api", tags=["auth"])


class RegisterRequest(BaseModel):
    """注册请求模型"""
    username: str = Field(description="用户名", min_length=3, max_length=50)
    password: str = Field(description="密码", min_length=6, max_length=100)
    nickname: Optional[str] = Field(default=None, description="昵称")
    qq_user_id: Optional[str] = Field(default=None, description="QQ用户ID")
    avatar: Optional[str] = Field(default=None, description="头像URL")


class LoginRequest(BaseModel):
    """登录请求模型"""
    username: str = Field(description="用户名")
    password: str = Field(description="密码")


class UserResponse(BaseModel):
    """用户响应模型"""
    id: int
    username: str
    nickname: Optional[str]
    qq_user_id: Optional[str]
    avatar: Optional[str]
    is_active: int
    is_admin: int
    created_at: datetime
    
    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    """令牌响应模型"""
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


@router.post("/auth/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(request: RegisterRequest):
    """用户注册"""
    # 检查用户名是否已存在
    existing_user = await user_manager.get_user_by_username(request.username)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="用户名已存在"
        )
    
    # 检查QQ用户ID是否已存在
    if request.qq_user_id:
        existing_qq_user = await user_manager.get_user_by_qq_id(request.qq_user_id)
        if existing_qq_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="该QQ账号已注册"
            )
    
    # 创建用户
    user = await user_manager.create_user(
        username=request.username,
        password=request.password,
        nickname=request.nickname,
        qq_user_id=request.qq_user_id,
        avatar=request.avatar
    )
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="用户创建失败"
        )
    
    return UserResponse.model_validate(user)


@router.post("/auth/login", response_model=TokenResponse)
async def login(request: LoginRequest):
    """用户登录"""
    # 认证用户
    user = await user_manager.authenticate(request.username, request.password)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误"
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="账号已被禁用"
        )
    
    # 创建访问令牌
    token = auth_manager.create_token(
        user_id=user.id,
        username=user.username,
        qq_user_id=user.qq_user_id
    )
    
    return TokenResponse(
        access_token=token,
        user=UserResponse.model_validate(user)
    )


@router.get("/auth/me", response_model=UserResponse)
async def get_current_user(token: str = Depends(get_access_token)):
    """获取当前用户信息"""
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="缺少令牌")
    user_info = auth_manager.get_user_from_token(token)
    
    if not user_info:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的令牌"
        )
    
    user = await user_manager.get_user_by_id(user_info['user_id'])
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )
    
    return UserResponse.model_validate(user)


@router.post("/auth/qq-bind")
async def bind_qq_account(token: str = Depends(get_access_token), qq_user_id: str = ""):
    """绑定QQ账号"""
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="缺少令牌")
    if not qq_user_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="缺少 qq_user_id")
    user_info = auth_manager.get_user_from_token(token)
    
    if not user_info:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的令牌"
        )
    
    # 检查QQ用户ID是否已被绑定
    existing_user = await user_manager.get_user_by_qq_id(qq_user_id)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="该QQ账号已被绑定"
        )
    
    # 获取用户
    user = await user_manager.get_user_by_id(user_info['user_id'])
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )
    
    # 更新用户QQ ID
    success = await user_manager.update_user(
        user_id=user.id,
        qq_user_id=qq_user_id
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="绑定失败"
        )
    
    return {"message": "QQ账号绑定成功"}
