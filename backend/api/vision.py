from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Dict, Any, Optional
import base64

from ..core.bot import Bot

# 全局Bot实例
bot_instance = None

def get_bot() -> Bot:
    """获取Bot实例"""
    global bot_instance
    if bot_instance is None:
        bot_instance = Bot()
    return bot_instance

router = APIRouter(prefix="/api/vision", tags=["视觉识别"])


class VisionConfigRequest(BaseModel):
    """视觉识别配置请求"""
    enabled: bool = False
    provider: str = "modelscope"
    modelscope: Dict[str, Any] = {}
    instruction_text: str = "这是一张图片的描述，请根据描述生成一段合适的话语："
    auto_send_to_llm: bool = True
    follow_up_timeout: float = 5.0
    trigger_keywords: list = []
    error_message: str = "😢 图片识别失败：{error}"


class VisionRecognitionRequest(BaseModel):
    """视觉识别请求"""
    image_url: Optional[str] = None
    image_data: Optional[str] = None  # base64编码的图片数据
    prompt: Optional[str] = None


class VisionRecognitionResponse(BaseModel):
    """视觉识别响应"""
    success: bool
    message: str
    recognition_text: Optional[str] = None


@router.get("/config")
async def get_vision_config(bot: Bot = Depends(get_bot)):
    """获取视觉识别配置"""
    try:
        config = bot.get_vision_config()
        return {
            "success": True,
            "data": config
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/config")
async def update_vision_config(
    request: VisionConfigRequest,
    bot: Bot = Depends(get_bot)
):
    """更新视觉识别配置"""
    try:
        config_dict = request.dict()
        bot.update_vision_config(config_dict)
        return {
            "success": True,
            "message": "配置更新成功"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/recognize")
async def recognize_image(
    request: VisionRecognitionRequest,
    bot: Bot = Depends(get_bot)
):
    """识别图片"""
    try:
        image_data = None
        if request.image_data:
            # 解码base64图片数据
            image_data = base64.b64decode(request.image_data)
        
        recognition_text = await bot.recognize_image(
            image_url=request.image_url,
            image_data=image_data,
            prompt=request.prompt
        )
        
        return VisionRecognitionResponse(
            success=True,
            message="图片识别成功",
            recognition_text=recognition_text
        )
    except Exception as e:
        return VisionRecognitionResponse(
            success=False,
            message=f"图片识别失败：{str(e)}"
        )


@router.post("/test-connection")
async def test_connection(bot: Bot = Depends(get_bot)):
    """测试视觉识别连接"""
    try:
        success = await bot.test_vision_connection()
        return {
            "success": success,
            "message": "连接成功" if success else "连接失败"
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"连接测试失败：{str(e)}"
        }