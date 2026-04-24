from __future__ import annotations

import re
from typing import Optional, Tuple


_GEN_IMG_TAG_RE = re.compile(r"\[GEN_IMG:\s*(.*?)\]", re.IGNORECASE | re.DOTALL)
_PROMPT_LABEL_RE = re.compile(r"(?:提示词|prompt)\s*[:：]\s*(.+)$", re.IGNORECASE | re.DOTALL)
_BRACKET_IMAGE_GEN_RE = re.compile(r"^\s*\[[^\]]*图片生成[^\]]*\]\s*", re.IGNORECASE)


def extract_gen_img_prompt(text: str) -> Tuple[str, Optional[str]]:
    """从文本中提取 [GEN_IMG: ...] 生图指令，并返回(清理后的文本, 提示词)。

    兼容一些模型会在标签后追加的格式，例如：
      - [GEN_IMG: 场景][图片生成] 提示词：更详细的提示词
      - [GEN_IMG: ...] prompt: ...
    """
    if not text:
        return "", None

    matches = list(_GEN_IMG_TAG_RE.finditer(text))
    if not matches:
        return text, None

    last = matches[-1]
    tag_prompt = (last.group(1) or "").strip()

    suffix = text[last.end():]
    suffix_stripped = suffix.strip()

    # 有些模型会在标签后输出 “[图片生成] 提示词：...”，优先使用该部分的提示词
    suffix_prompt: Optional[str] = None
    label_match = _PROMPT_LABEL_RE.search(suffix_stripped)
    if label_match:
        suffix_prompt = (label_match.group(1) or "").strip()

    prompt = suffix_prompt or tag_prompt

    # 生成“展示给用户”的文本：移除 GEN_IMG 标签，且若后缀明显是生图元信息则一并丢弃
    prefix = text[:last.start()].rstrip()

    looks_like_meta = False
    if suffix_stripped:
        if "提示词" in suffix_stripped or "prompt" in suffix_stripped.lower():
            looks_like_meta = True
        else:
            # 允许重复的 [图片生成] / [图片生成请求] / [图片生成结果] 等
            tmp = suffix_stripped
            while _BRACKET_IMAGE_GEN_RE.match(tmp):
                tmp = _BRACKET_IMAGE_GEN_RE.sub("", tmp, count=1).lstrip()
            if not tmp:
                looks_like_meta = True

    if looks_like_meta:
        cleaned = prefix
    else:
        cleaned = (prefix + suffix).strip()

    cleaned = _GEN_IMG_TAG_RE.sub("", cleaned).rstrip()

    if not prompt:
        return cleaned, None
    return cleaned, prompt

