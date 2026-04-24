"""
启航AI TTS 提供商
"""

import aiohttp
import asyncio
from typing import Dict, Any, Optional, List
from ..base import BaseTTSProvider
import logging

logger = logging.getLogger(__name__)


class QihangTTSProvider(BaseTTSProvider):
    """启航AI TTS 提供商"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.api_base = config.get('api_base', 'https://api.qhaigc.net/v1')
        self.api_key = config.get('api_key', '')
        self.model = config.get('model', 'qhai-tts')
        self.default_voice = config.get('voice', '柔情萝莉')
    
    async def synthesize(self, text: str, voice: Optional[str] = None) -> bytes:
        """
        合成语音
        
        Args:
            text: 要合成的文本
            voice: 语音角色，可选
            
        Returns:
            bytes: 音频数据
            
        Raises:
            Exception: 合成失败时抛出异常
        """
        if not self.api_key:
            raise ValueError("启航AI API密钥未配置")
        
        voice = voice or self.default_voice
        
        headers = {
            'Authorization': self.api_key,
            'Content-Type': 'application/json'
        }
        
        data = {
            'model': self.model,
            'input': text,
            'voice': voice
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.api_base}/audio/speech",
                    headers=headers,
                    json=data
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"启航AI TTS 请求失败: {response.status} - {error_text}")
                        raise Exception(f"启航AI TTS 请求失败: {response.status}")
                    
                    audio_data = await response.read()
                    logger.info(f"启航AI TTS 合成成功，文本长度: {len(text)}，音频大小: {len(audio_data)}")
                    return audio_data
                    
        except aiohttp.ClientError as e:
            logger.error(f"启航AI TTS 网络请求失败: {str(e)}")
            raise Exception(f"启航AI TTS 网络请求失败: {str(e)}")
        except Exception as e:
            logger.error(f"启航AI TTS 合成失败: {str(e)}")
            raise Exception(f"启航AI TTS 合成失败: {str(e)}")

    def _extract_voices_from_response(self, result: Any) -> List[Dict[str, str]]:
        """尽可能兼容不同返回格式，提取语音列表"""
        voices: List[Dict[str, str]] = []
        candidates = []

        if isinstance(result, dict):
            if isinstance(result.get('voice_characters'), list):
                candidates = result.get('voice_characters', [])
            elif isinstance(result.get('data'), list):
                candidates = result.get('data', [])
            elif isinstance(result.get('voices'), list):
                candidates = result.get('voices', [])
        elif isinstance(result, list):
            candidates = result

        for item in candidates:
            if isinstance(item, dict):
                name = item.get('name') or item.get('id') or item.get('voice') or ''
                description = item.get('description') or item.get('desc') or ''
                if name:
                    voices.append({'name': name, 'description': description})
            elif isinstance(item, str):
                voices.append({'name': item, 'description': ''})

        return voices
    
    async def get_voices(self) -> List[Dict[str, str]]:
        """
        获取可用语音角色列表

        Returns:
            List[Dict[str, str]]: 语音角色列表，包含 name 和 description
        """
        if not self.api_key:
            raise ValueError("启航AI API密钥未配置")

        headers = {
            'Authorization': self.api_key
        }

        # 默认兜底列表，保证界面可用
        fallback_voices = [{
            'name': self.default_voice,
            'description': '默认音色'
        }]

        # 逐个尝试可能的接口路径，兼容不同版本
        base_url = self.api_base.rstrip('/')
        candidate_endpoints = [
            f"{base_url}/models",  # 实际可用的路径，返回所有模型列表
            f"{base_url}/voice/models/list",  # 调用指南中的正式路径
            f"{base_url}/voice.models/list",
            f"{base_url}/voices",
            f"{base_url}/voice_models",
        ]

        try:
            async with aiohttp.ClientSession() as session:
                for endpoint in candidate_endpoints:
                    try:
                        async with session.get(endpoint, headers=headers) as response:
                            if response.status == 404:
                                logger.warning(f"语音列表接口不存在: {endpoint}")
                                continue
                            if response.status != 200:
                                error_text = await response.text()
                                logger.error(f"获取启航AI语音列表失败[{endpoint}]: {response.status} - {error_text}")
                                continue

                            result = await response.json()

                            # 尝试从 /v1/models API中提取TTS语音角色
                            # 返回格式: {"data": [{"id": "qhai-tts:角色名", "description": "..."}, ...]}
                            if endpoint.endswith('/models') and isinstance(result, dict):
                                models = result.get('data', [])
                                voices = []
                                for model in models:
                                    model_id = model.get('id', '')
                                    # 解析 qhai-tts:角色名 格式
                                    if model_id.startswith('qhai-tts:'):
                                        # 直接从模型ID中提取角色名
                                        voice_name = model_id.split(':', 1)[1] if ':' in model_id else model_id
                                        description = model.get('description', '')
                                        # 清理描述，只保留简短描述
                                        if description:
                                            # 提取"角色"后面的内容作为简短描述
                                            import re
                                            match = re.search(r'角色["\s]*[:：]["\s]*([^"]+?)[，,。]', description)
                                            if match:
                                                description = match.group(1).strip()
                                        voices.append({
                                            'name': voice_name,
                                            'description': description
                                        })

                                if voices:
                                    logger.info(f"获取启航AI语音列表成功（{endpoint}），共 {len(voices)} 个语音角色")
                                    return voices
                                logger.warning(f"启航AI语音列表返回为空（{endpoint}），使用兜底列表")
                            else:
                                # 尝试其他格式
                                voices = self._extract_voices_from_response(result)
                                if voices:
                                    logger.info(f"获取启航AI语音列表成功（{endpoint}），共 {len(voices)} 个语音角色")
                                    return voices
                                logger.warning(f"启航AI语音列表返回为空（{endpoint}），使用兜底列表")
                    except aiohttp.ClientError as e:
                        logger.error(f"获取启航AI语音列表网络异常[{endpoint}]: {str(e)}")
                        continue
                    except Exception as e:
                        logger.error(f"处理启航AI语音列表响应失败[{endpoint}]: {str(e)}")
                        continue

            logger.warning("所有语音列表接口均不可用，返回默认音色列表")
            return fallback_voices

        except aiohttp.ClientError as e:
            logger.error(f"获取启航AI语音列表网络请求失败: {str(e)}")
            return fallback_voices
        except Exception as e:
            logger.error(f"获取启航AI语音列表失败: {str(e)}")
            return fallback_voices
            return fallback_voices
    
    async def test_connection(self) -> bool:
        """
        测试连接
        
        Returns:
            bool: 连接是否成功
        """
        try:
            # 尝试获取语音列表来测试连接
            await self.get_voices()
            return True
        except Exception as e:
            logger.error(f"启航AI TTS 连接测试失败: {str(e)}")
            return False
