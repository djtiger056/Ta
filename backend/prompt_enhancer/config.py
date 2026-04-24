from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class IntentRule(BaseModel):
    """意图配置：用于关键词匹配和分类增强映射"""
    name: str
    description: str = ""
    enabled: bool = True
    keywords: List[str] = Field(default_factory=list)
    categories: List[str] = Field(default_factory=list)
    pick_count_overrides: Dict[str, int] = Field(default_factory=dict)


class PresetConfig(BaseModel):
    """预设配置"""
    name: str
    description: str
    outfit_style: str = "random"
    scene_type: str = "random"
    enabled: bool = True
    categories: List[str] = Field(default_factory=list)
    pick_count_overrides: Dict[str, int] = Field(default_factory=dict)


class WordBankItem(BaseModel):
    """词库词条"""
    text: str
    enabled: bool = True
    weight: int = 1  # 权重，用于概率调整


class WordBankCategory(BaseModel):
    """词库分类"""
    path: str  # 分类路径，如 "portrait.hairstyle"
    name: str  # 显示名称
    enabled: bool = True
    pick_count: int = 1
    items: List[WordBankItem] = Field(default_factory=list)
    is_builtin: bool = False  # 是否内置分类


class PromptEnhancerConfig(BaseModel):
    """提示词增强配置"""

    enabled: bool = True
    mode: str = Field(
        default="random",
        description="random: 词库随机增强; smart: 预留给 LLM 智能增强",
    )
    # 可配置的意图规则（多目的增强）
    intents: List[IntentRule] = Field(
        default_factory=lambda: [
            IntentRule(
                name="portrait",
                description="人像/自拍增强",
                keywords=[
                    "自拍",
                    "人像",
                    "照片",
                    "美女",
                    "美照",
                    "街拍",
                    "帅哥",
                    "形象",
                    "portrait",
                    "selfie",
                    "photo",
                    "girl",
                    "boy",
                    "woman",
                    "man",
                ],
                categories=[
                    "hairstyle",
                    "outfit",
                    "facial_features",
                    "pose",
                    "expression",
                    "scene",
                    "lighting",
                    "quality_boost",
                ],
                pick_count_overrides={},
            ),
            IntentRule(
                name="landscape",
                description="风景/自然/城市场景增强",
                keywords=[
                    "风景",
                    "山",
                    "湖",
                    "海",
                    "森林",
                    "草地",
                    "河流",
                    "城市",
                    "街景",
                    "日落",
                    "夕阳",
                    "天空",
                    "cloud",
                    "sky",
                    "sunset",
                    "landscape",
                    "cityscape",
                    "mountain",
                    "lake",
                    "beach",
                ],
                categories=[
                    "scene",
                    "lighting",
                    "quality_boost",
                ],
                pick_count_overrides={},
            ),
        ]
    )
    categories: Dict[str, bool] = Field(default_factory=dict)
    pick_count: Dict[str, int] = Field(default_factory=dict)
    
    # 自定义预设
    presets: List[PresetConfig] = Field(
        default_factory=lambda: [
            PresetConfig(
                name="casual_cute",
                description="休闲可爱",
                outfit_style="casual",
                scene_type="indoor",
                categories=["hairstyle", "outfit", "facial_features", "pose", "expression", "scene", "lighting", "quality"],
                pick_count_overrides={"hairstyle": 1, "outfit": 1, "facial_features": 1, "pose": 1, "expression": 1, "scene": 1, "lighting": 1, "quality": 1}
            ),
            PresetConfig(
                name="formal_elegant", 
                description="正式优雅",
                outfit_style="formal",
                scene_type="indoor",
                categories=["hairstyle", "outfit", "facial_features", "pose", "expression", "scene", "lighting", "quality"],
                pick_count_overrides={"hairstyle": 1, "outfit": 1, "facial_features": 1, "pose": 1, "expression": 1, "scene": 1, "lighting": 1, "quality": 1}
            ),
            PresetConfig(
                name="fresh_outdoor",
                description="清新户外", 
                outfit_style="casual",
                scene_type="outdoor",
                categories=["hairstyle", "outfit", "facial_features", "pose", "expression", "scene", "lighting", "quality"],
                pick_count_overrides={"hairstyle": 1, "outfit": 1, "facial_features": 1, "pose": 1, "expression": 1, "scene": 1, "lighting": 1, "quality": 1}
            ),
            PresetConfig(
                name="portrait_default",
                description="人像默认",
                outfit_style="cute",
                scene_type="random",
                categories=["hairstyle", "outfit", "facial_features", "pose", "expression", "scene", "lighting", "quality"],
                pick_count_overrides={"hairstyle": 1, "outfit": 1, "facial_features": 1, "pose": 1, "expression": 1, "scene": 1, "lighting": 1, "quality": 1}
            )
        ]
    )
    current_preset: str = Field(default="portrait_default")
    
    # 词库文件路径
    builtin_word_bank_path: str = Field(
        default="backend/prompt_enhancer/word_banks/portrait.yaml",
        description="内置词库文件路径",
    )
    custom_word_bank_path: str = Field(
        default="data/custom_prompt_words.yaml",
        description="自定义词库文件路径",
    )
    
    # 是否允许编辑内置词库
    allow_edit_builtin: bool = Field(default=True)

    class Config:
        extra = "ignore"
