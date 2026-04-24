from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Dict, Any, Optional
import base64

from ..core.bot import Bot
from backend.api.deps import get_access_token
from backend.user.auth import auth_manager

# 全局Bot实例
bot_instance = None

def get_bot() -> Bot:
    """获取Bot实例"""
    global bot_instance
    if bot_instance is None:
        bot_instance = Bot()
    return bot_instance

router = APIRouter(prefix="/api/image-gen", tags=["图像生成"])


class ImageGenConfigRequest(BaseModel):
    """图像生成配置请求"""
    enabled: bool = True
    provider: str = "modelscope"
    modelscope: Dict[str, Any] = {}
    yunwu: Dict[str, Any] = {}
    trigger_keywords: list = []
    generating_message: str = "🎨 正在为你生成图片，请稍候..."
    error_message: str = "😢 图片生成失败：{error}"
    success_message: str = "✨ 图片已生成完成！"


class ImageGenRequest(BaseModel):
    """图像生成请求"""
    prompt: str
    user_id: Optional[str] = None


class ImageGenResponse(BaseModel):
    """图像生成响应"""
    success: bool
    message: str
    image_data: Optional[str] = None  # base64编码的图片数据


@router.get("/config")
async def get_image_gen_config(bot: Bot = Depends(get_bot)):
    """获取图像生成配置"""
    try:
        config = bot.get_image_gen_config()
        return {
            "success": True,
            "data": config
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/config")
async def update_image_gen_config(
    request: ImageGenConfigRequest,
    bot: Bot = Depends(get_bot)
):
    """更新图像生成配置"""
    try:
        config_dict = request.dict()
        bot.update_image_gen_config(config_dict)
        return {
            "success": True,
            "message": "配置更新成功"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate")
async def generate_image(
    request: ImageGenRequest,
    bot: Bot = Depends(get_bot),
    token: str = Depends(get_access_token),
):
    """生成图像"""
    try:
        effective_user_id = request.user_id or "web_image_user"
        if token:
            user_info = auth_manager.get_user_from_token(token)
            if user_info:
                # 优先用 qq_user_id（若已绑定），否则回退到 user_id（数字）
                effective_user_id = str(user_info.get("qq_user_id") or user_info.get("user_id") or effective_user_id)

        image_data = await bot.generate_image(request.prompt, user_id=effective_user_id)
        
        if image_data:
            # 将图片转换为base64
            base64_data = base64.b64encode(image_data).decode('utf-8')
            return ImageGenResponse(
                success=True,
                message="图片生成成功",
                image_data=base64_data
            )
        else:
            return ImageGenResponse(
                success=False,
                message="图片生成失败"
            )
    except Exception as e:
        return ImageGenResponse(
            success=False,
            message=f"图片生成失败：{str(e)}"
        )


@router.post("/test-connection")
async def test_connection(bot: Bot = Depends(get_bot)):
    """测试图像生成连接"""
    try:
        success = await bot.test_image_gen_connection()
        return {
            "success": success,
            "message": "连接成功" if success else "连接失败"
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"连接测试失败：{str(e)}"
        }
