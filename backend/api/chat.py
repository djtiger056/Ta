from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Dict, Any
import json
import time

router = APIRouter(prefix="/api", tags=["chat"])

# 共享Bot实例和当前LLM签名（用于热更新）
_bot_instance = None
_llm_signature = None

def _current_llm_signature():
    """生成当前LLM配置的签名，用于判断是否需要重建Bot"""
    import json
    from ..config import config

    # 重新加载配置，确保与文件一致
    config.refresh_from_file()

    llm_cfg = config.llm_config
    provider = llm_cfg.get('provider')
    provider_cfg = llm_cfg.get(provider, {}) if isinstance(llm_cfg, dict) else {}

    # 包含全局字段以及提供商专属字段变化
    return (
        provider,
        llm_cfg.get('model'),
        llm_cfg.get('api_base'),
        llm_cfg.get('api_key'),
        llm_cfg.get('temperature'),
        llm_cfg.get('max_tokens'),
        json.dumps(provider_cfg, sort_keys=True, ensure_ascii=False),
    )

def get_bot():
    """获取共享Bot实例；LLM配置变化时自动重建"""
    global _bot_instance, _llm_signature
    signature = _current_llm_signature()
    if _bot_instance is None or _llm_signature != signature:
        from ..core.bot import Bot
        _bot_instance = Bot()
        _llm_signature = signature
    return _bot_instance

def reset_bot():
    """重置Bot实例，方便在配置变更后重新创建"""
    global _bot_instance, _llm_signature
    _bot_instance = None
    _llm_signature = None

class ChatRequest(BaseModel):
    message: str
    user_id: str = "web_user"

def _detect_audio_mime(audio_data: bytes) -> str:
    if not audio_data:
        return "audio/mpeg"
    if audio_data[:4] == b"RIFF" and audio_data[8:12] == b"WAVE":
        return "audio/wav"
    if audio_data[:4] == b"OggS":
        return "audio/ogg"
    return "audio/mpeg"

@router.post("/chat")
async def chat(request: ChatRequest):
    """普通聊天接口"""
    try:
        bot = get_bot()
        response = await bot.chat(request.message, request.user_id)

        # 获取生成的图片（如果有）
        last_image = bot.get_last_generated_image()
        image_base64 = None
        if last_image and last_image.get("image_data"):
            import base64
            image_base64 = base64.b64encode(last_image["image_data"]).decode('utf-8')
            print(f"[Chat API] 返回生成的图片，大小: {len(last_image['image_data'])} bytes")

        # 尝试合成语音
        try:
            audio_data = await bot.synthesize_speech(response, user_id=request.user_id)
            audio_base64 = None
            audio_mime = None
            voice_only = bot.is_voice_only_mode(request.user_id)
            text_to_send = response

            if audio_data:
                import base64
                audio_base64 = base64.b64encode(audio_data).decode('utf-8')
                audio_mime = _detect_audio_mime(audio_data)
                print(f"TTS音频生成成功，大小: {len(audio_data)} bytes")
                if voice_only:
                    text_to_send = bot.strip_tts_text(response, request.user_id)
            else:
                print("TTS未生成音频（可能被概率或配置阻止）")
                text_to_send = response
        except Exception as e:
            print(f"TTS生成失败: {str(e)}")
            audio_base64 = None
            audio_mime = None
            voice_only = False
            text_to_send = response

        emote_payload = None
        try:
            emote_payload = bot.maybe_get_emote_payload(request.message, response)
        except Exception as e:
            print(f"选择表情包失败: {str(e)}")

        return {
            "response": text_to_send,
            "audio": audio_base64,
            "audio_mime": audio_mime,
            "voice_only": bool(audio_base64 and voice_only),
            "emote": emote_payload,
            "image": image_base64
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"聊天失败: {str(e)}")

@router.post("/chat/stream")
async def chat_stream(request: ChatRequest):
    """流式聊天接口"""
    async def generate():
        request_start = time.perf_counter()

        def elapsed_ms() -> float:
            return round((time.perf_counter() - request_start) * 1000, 2)

        def meta_event(stage: str, extra: Dict[str, Any] | None = None) -> str:
            payload: Dict[str, Any] = {
                "meta": {
                    "stage": stage,
                    "elapsed_ms": elapsed_ms(),
                    "server_ts": time.time(),
                }
            }
            if extra:
                payload["meta"].update(extra)
            return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"

        try:
            yield meta_event("server_request_received")
            bot = get_bot()
            yield meta_event("bot_ready")
            full_response = ""
            first_chunk_seen = False

            # 流式输出文本
            async for chunk in bot.chat_stream(request.message, request.user_id):
                if not first_chunk_seen:
                    yield meta_event("first_model_chunk")
                    first_chunk_seen = True
                full_response += chunk
                yield f"data: {json.dumps({'content': chunk})}\n\n"

            yield meta_event("llm_stream_done", {"response_chars": len(full_response)})

            # 获取生成的图片（如果有）
            last_image = bot.get_last_generated_image()
            if last_image and last_image.get("image_data"):
                import base64
                image_base64 = base64.b64encode(last_image["image_data"]).decode('utf-8')
                print(f"[Chat Stream API] 返回生成的图片，大小: {len(last_image['image_data'])} bytes")
                yield f"data: {json.dumps({'image': image_base64})}\n\n"

            # 完成文本输出后，尝试合成语音
            try:
                audio_data = await bot.synthesize_speech(full_response, user_id=request.user_id)
                if audio_data:
                    import base64
                    audio_base64 = base64.b64encode(audio_data).decode('utf-8')
                    print(f"流式TTS音频生成成功，大小: {len(audio_data)} bytes")
                    yield f"data: {json.dumps({'audio': audio_base64, 'audio_mime': _detect_audio_mime(audio_data), 'voice_only': bot.is_voice_only_mode(request.user_id)})}\n\n"
                else:
                    print("流式TTS未生成音频")
            except Exception as e:
                print(f"流式TTS生成失败: {str(e)}")

            try:
                emote_payload = bot.maybe_get_emote_payload(request.message, full_response)
                if emote_payload:
                    yield f"data: {json.dumps({'emote': emote_payload})}\n\n"
            except Exception as e:
                print(f"选择表情包失败: {str(e)}")

            yield meta_event("stream_done")
            yield "data: [DONE]\n\n"
        except Exception as e:
            yield meta_event("stream_error", {"error": str(e)})
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
