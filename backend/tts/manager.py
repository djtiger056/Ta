"""
TTS 管理器
"""

import asyncio
import random
import re
from typing import Dict, Any, Optional, List, Tuple
from .base import BaseTTSProvider
from .providers.qihang import QihangTTSProvider
from .providers.qwen import QwenTTSProvider
from .config import TTSConfig, TTSTextCleaningConfig
from .text_cleaner import TTSTextCleaner
import logging

logger = logging.getLogger(__name__)


class TTSManager:
    """TTS 管理器"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = TTSConfig(**config)
        self.provider = self._create_provider()
        self.text_cleaner = TTSTextCleaner(
            TTSTextCleaningConfig(**self.config.text_cleaning)
        )
        self._last_selected_text: Optional[str] = None
        self._last_selected_sentence_count: int = 0
        self._last_synthesized_text: Optional[str] = None
    
    def _create_provider(self) -> BaseTTSProvider:
        """创建TTS提供商"""
        if self.config.provider == "qihang":
            return QihangTTSProvider(self.config.qihang)
        if self.config.provider == "qwen":
            return QwenTTSProvider(self.config.qwen)
        else:
            raise ValueError(f"不支持的TTS提供商: {self.config.provider}")
    
    async def synthesize(self, text: str, voice: Optional[str] = None) -> bytes:
        """
        合成语音
        
        Args:
            text: 要合成的文本
            voice: 语音角色，可选
            
        Returns:
            bytes: 音频数据
        """
        self._last_synthesized_text = None

        if not self.config.enabled:
            raise ValueError("TTS功能未启用")
        
        # 文本清洗
        cleaned_text = self.text_cleaner.clean(text)
        if not cleaned_text.strip():
            logger.warning("清洗后文本为空，跳过TTS")
            return b''
        
        # 分段处理
        if self.config.segment_config.get('enabled', False):
            segments = self._split_text(cleaned_text)
            # 目前只返回第一段，后续可以实现多段处理
            text_to_synthesize = segments[0] if segments else cleaned_text
        else:
            text_to_synthesize = cleaned_text

        self._last_synthesized_text = text_to_synthesize

        return await self.provider.synthesize(text_to_synthesize, voice)
    
    def _split_text(self, text: str) -> List[str]:
        """
        分段文本
        
        Args:
            text: 原始文本
            
        Returns:
            List[str]: 分段后的文本列表
        """
        segment_config = self.config.segment_config
        max_length = segment_config.get('max_segment_length', 100)
        min_length = segment_config.get('min_segment_length', 5)
        max_segments = segment_config.get('max_segments', 1)
        strategy = segment_config.get('strategy', 'last')
        
        if len(text) <= max_length:
            return [text]
        
        # 按句号、问号、感叹号分割
        sentences = re.split(r'[。！？.!?]', text)
        sentences = [s.strip() for s in sentences if s.strip()]
        
        segments = []
        current_segment = ""
        
        for sentence in sentences:
            if len(current_segment + sentence) <= max_length:
                current_segment += sentence + "。"
            else:
                if current_segment:
                    segments.append(current_segment.strip())
                current_segment = sentence + "。"
        
        if current_segment:
            segments.append(current_segment.strip())
        
        # 过滤过短的段落
        segments = [s for s in segments if len(s) >= min_length]
        
        # 限制段数
        if len(segments) > max_segments:
            if strategy == "first":
                segments = segments[:max_segments]
            elif strategy == "last":
                segments = segments[-max_segments:]
            elif strategy == "middle":
                start = (len(segments) - max_segments) // 2
                segments = segments[start:start + max_segments]
        
        return segments
    
    async def get_voices(self) -> List[Dict[str, str]]:
        """
        获取可用语音角色列表
        
        Returns:
            List[Dict[str, str]]: 语音角色列表
        """
        return await self.provider.get_voices()
    
    async def test_connection(self) -> bool:
        """
        测试连接
        
        Returns:
            bool: 连接是否成功
        """
        return await self.provider.test_connection()
    
    def should_trigger_tts(self) -> bool:
        """
        判断是否应该触发TTS
        
        Returns:
            bool: 是否触发TTS
        """
        if not self.config.enabled:
            return False
        
        probability = self.config.probability
        return random.random() <= probability
    
    def _choose_strategy(self) -> str:
        """按照配置的权重选择播报策略"""
        rand_cfg = self.config.randomization
        if not rand_cfg.enabled:
            return "full"
        
        weights = {
            "full": max(rand_cfg.full_probability, 0),
            "partial": max(rand_cfg.partial_probability, 0),
            "none": max(rand_cfg.none_probability, 0),
        }
        total = sum(weights.values())
        if total <= 0:
            return "full"
        
        threshold = random.random() * total
        cumulative = 0.0
        for key, weight in weights.items():
            cumulative += weight
            if threshold <= cumulative:
                return key
        return "full"
    
    def _split_sentences_for_partial(self, text: str) -> List[str]:
        """将文本按句子拆分，保留标点"""
        # 捕获句子及结尾标点，避免丢失语气
        sentences = re.findall(r'[^。！？!?]+[。！？!?]?', text)
        return [s.strip() for s in sentences if s.strip()]
    
    def _select_partial_sentences(self, text: str) -> Tuple[Optional[str], int]:
        """从文本中挑选部分句子，优先末尾以避免播报顺序错位"""
        sentences = self._split_sentences_for_partial(text)
        if not sentences:
            return None, 0
        
        cfg = self.config.randomization
        min_count = max(1, cfg.min_partial_sentences)
        max_count = max(min_count, cfg.max_partial_sentences)
        
        max_count = min(max_count, len(sentences))
        min_count = min(min_count, len(sentences))
        
        pick_count = random.randint(min_count, max_count)
        start_index = max(len(sentences) - pick_count, 0)
        # 末尾连续句子更贴近最新文本，减少语音延迟带来的割裂感
        selected = sentences[start_index:]
        return "".join(selected), len(selected)
    
    def select_text_for_tts(self, text: str) -> Optional[str]:
        """
        根据随机策略选择要播报的文本
        
        Returns:
            清洗后的文本；如果不播报返回None
        """
        self._last_selected_text = None
        self._last_selected_sentence_count = 0

        if not self.should_trigger_tts():
            return None
        
        cleaned_text = self.text_cleaner.clean(text)
        if not cleaned_text.strip():
            logger.warning("清洗后文本为空，跳过TTS")
            return None
        
        strategy = self._choose_strategy()
        if strategy == "none":
            return None
        if strategy == "partial":
            partial, sentence_count = self._select_partial_sentences(cleaned_text)
            selected = partial or cleaned_text
            self._last_selected_text = selected
            self._last_selected_sentence_count = sentence_count or len(self._split_sentences_for_partial(selected)) or 1
            return selected

        self._last_selected_text = cleaned_text
        self._last_selected_sentence_count = len(self._split_sentences_for_partial(cleaned_text)) or 1
        return cleaned_text
    
    def get_remaining_text(self, original_text: str) -> str:
        """
        返回移除已用于TTS的句子后的文本（用于避免重复播报）
        """
        if not original_text or (not self._last_selected_text and self._last_selected_sentence_count <= 0):
            return original_text

        # 优先按“末尾句子数”剔除，避免部分播报时因空格/换行导致子串不匹配
        if self._last_selected_sentence_count > 0:
            original_sentences = self._split_sentences_for_partial(original_text)
            if original_sentences:
                k = min(self._last_selected_sentence_count, len(original_sentences))
                remaining = "".join(original_sentences[:-k]).strip()
                remaining = re.sub(r'\s+', ' ', remaining).strip()
                return remaining

        # 兜底：子串替换
        if self._last_selected_text and self._last_selected_text in original_text:
            remaining = original_text.replace(self._last_selected_text, "", 1)
            remaining = re.sub(r'\s+', ' ', remaining).strip()
            return remaining

        return original_text

    def get_last_synthesized_text(self) -> Optional[str]:
        """获取最近一次实际送入TTS提供商的文本。"""
        return self._last_synthesized_text
    
    def get_config(self) -> Dict[str, Any]:
        """获取配置"""
        return self.config.dict()
    
    def update_config(self, config: Dict[str, Any]):
        """更新配置"""
        self.config = TTSConfig(**config)
        self.provider = self._create_provider()
        self.text_cleaner = TTSTextCleaner(
            TTSTextCleaningConfig(**self.config.text_cleaning)
        )
