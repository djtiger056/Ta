import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.core.gen_img_parser import extract_gen_img_prompt


def test_extract_gen_img_prompt_at_end():
    cleaned, prompt = extract_gen_img_prompt("你好呀\n[GEN_IMG: 一只猫]\n")
    assert cleaned == "你好呀"
    assert prompt == "一只猫"


def test_extract_gen_img_prompt_with_meta_suffix_uses_label_prompt():
    text = "辛苦啦！[GEN_IMG: 宿舍书桌][图片生成] 提示词：更详细的提示词"
    cleaned, prompt = extract_gen_img_prompt(text)
    assert cleaned == "辛苦啦！"
    assert prompt == "更详细的提示词"


def test_extract_gen_img_prompt_with_only_bracket_meta_suffix_drops_suffix():
    cleaned, prompt = extract_gen_img_prompt("hi [GEN_IMG: p] [图片生成结果]")
    assert cleaned == "hi"
    assert prompt == "p"


def test_extract_gen_img_prompt_keeps_non_meta_suffix():
    cleaned, prompt = extract_gen_img_prompt("hi [GEN_IMG: p] 另外我想说一句")
    assert cleaned == "hi 另外我想说一句"
    assert prompt == "p"


def test_extract_gen_img_prompt_empty_prompt_strips_tag_but_returns_none():
    cleaned, prompt = extract_gen_img_prompt("hi [GEN_IMG:   ][图片生成] 提示词：   ")
    assert cleaned == "hi"
    assert prompt is None
