"""
文本分割工具
"""

import re
from typing import List


def split_text_by_sentences(text: str, max_length: int = 100, min_length: int = 5) -> List[str]:
    """
    按句子分割文本，确保每段不超过最大长度
    
    Args:
        text: 原始文本
        max_length: 每段最大长度
        min_length: 每段最小长度（低于此长度的段将被忽略）
        
    Returns:
        分割后的文本列表
    """
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
    
    return segments


def split_text_by_length(text: str, max_length: int = 100) -> List[str]:
    """
    按固定长度分割文本
    
    Args:
        text: 原始文本
        max_length: 每段最大长度
        
    Returns:
        分割后的文本列表
    """
    if len(text) <= max_length:
        return [text]
    
    segments = []
    start = 0
    text_length = len(text)
    
    while start < text_length:
        end = start + max_length
        if end >= text_length:
            segments.append(text[start:])
            break
        
        # 尝试在标点符号处分割
        last_punctuation = max(
            text.rfind('。', start, end),
            text.rfind('！', start, end),
            text.rfind('？', start, end),
            text.rfind('.', start, end),
            text.rfind('!', start, end),
            text.rfind('?', start, end),
            text.rfind('，', start, end),
            text.rfind(',', start, end),
            text.rfind(';', start, end),
            text.rfind('；', start, end),
            text.rfind(' ', start, end),
            text.rfind('\n', start, end)
        )
        
        if last_punctuation > start and last_punctuation - start > max_length * 0.5:
            end = last_punctuation + 1
        
        segments.append(text[start:end].strip())
        start = end
    
    return segments


def smart_split_text(text: str, max_length: int = 100, min_length: int = 5, strategy: str = 'sentence') -> List[str]:
    """
    智能文本分割
    
    Args:
        text: 原始文本
        max_length: 每段最大长度
        min_length: 每段最小长度
        strategy: 分割策略，'sentence' 或 'length'
        
    Returns:
        分割后的文本列表
    """
    # 保护图片URL不被分割
    text = protect_image_urls(text)
    
    if strategy == 'sentence':
        return split_text_by_sentences(text, max_length, min_length)
    elif strategy == 'length':
        return split_text_by_length(text, max_length)
    else:
        raise ValueError(f"不支持的策略: {strategy}")


def protect_image_urls(text: str) -> str:
    """
    保护文本中的图片URL，用占位符替换，避免被分割算法破坏
    
    Args:
        text: 包含图片URL的文本
        
    Returns:
        替换后的文本
    """
    import re
    
    # 匹配Markdown格式的图片: ![alt](url) 或 [image](url)
    image_pattern = r'(\[([^\]]*)\]\((https?://[^\s)]+)\))'
    
    # 找到所有图片URL并替换为占位符
    protected_urls = []
    placeholder_counter = 0
    
    def replace_with_placeholder(match):
        nonlocal placeholder_counter
        placeholder = f"__IMAGE_PLACEHOLDER_{placeholder_counter}__"
        placeholder_counter += 1
        protected_urls.append((placeholder, match.group(0)))
        return placeholder
    
    # 替换图片URL
    protected_text = re.sub(image_pattern, replace_with_placeholder, text)
    
    # 恢复图片URL（确保完整URL不被分割）
    for placeholder, original_url in protected_urls:
        # 检查占位符是否被分割
        if placeholder in protected_text:
            protected_text = protected_text.replace(placeholder, original_url)
    
    return protected_text
