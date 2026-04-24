"""
TTS 文本清洗工具
"""

import re
from typing import Optional
from .config import TTSTextCleaningConfig


class TTSTextCleaner:
    """TTS 文本清洗器"""
    
    def __init__(self, config: TTSTextCleaningConfig):
        self.config = config
        
        # 预编译正则表达式
        self.emoji_pattern = re.compile(
            "["
            "\U0001F600-\U0001F64F"  # emoticons
            "\U0001F300-\U0001F5FF"  # symbols & pictographs
            "\U0001F680-\U0001F6FF"  # transport & map symbols
            "\U0001F1E0-\U0001F1FF"  # flags (iOS)
            "\U00002702-\U000027B0"
            "\U000024C2-\U0001F251"
            "]+", flags=re.UNICODE
        )
        
        self.kaomoji_pattern = re.compile(
            r'[\(（][^\)\)]*[\)）]|[\[\[][^\]\]]*[\]\]]|[oO][\_\-][oO]|[oO][\^v\~][oO]|[>v][\_<][v<]|[>v][\_<][v<]|[Xx][Dd]|[;:][-^~]?[)DdPp\(\[]|[;:][-^~]?[)DdPp\(\[]',
            flags=re.UNICODE
        )
        
        self.action_pattern = re.compile(
            r'[\*「『].*?[\*」』]|【.*?】|\*.*?\*|「.*?」|『.*?』',
            flags=re.UNICODE
        )
        
        self.brackets_pattern = re.compile(
            r'[()（）\[\]【】\{\}《》〈〉]',
            flags=re.UNICODE
        )
        
        self.markdown_pattern = re.compile(
            r'[*_`#~]+|!\[.*?\]\(.*?\)|\[.*?\]\(.*?\)|```.*?```',
            flags=re.UNICODE
        )
    
    def clean(self, text: str) -> str:
        """
        清洗文本
        
        Args:
            text: 原始文本
            
        Returns:
            str: 清洗后的文本
        """
        if not self.config.enabled:
            return text
        
        # 限制长度
        if len(text) > self.config.max_length:
            text = text[:self.config.max_length] + "..."
        
        # 移除emoji
        if self.config.remove_emoji:
            text = self.emoji_pattern.sub('', text)
        
        # 移除颜文字
        if self.config.remove_kaomoji:
            text = self.kaomoji_pattern.sub('', text)
        
        # 移除动作描述
        if self.config.remove_action_text:
            text = self.action_pattern.sub('', text)
        
        # 移除括号内容
        if self.config.remove_brackets_content:
            text = self.brackets_pattern.sub('', text)
        
        # 移除Markdown标记
        if self.config.remove_markdown:
            text = self.markdown_pattern.sub('', text)
        
        # 清理多余空格
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text