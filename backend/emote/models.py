from typing import List, Optional

from pydantic import BaseModel, Field, validator


class EmoteCategory(BaseModel):
    """表情包分类配置"""

    name: str = Field(..., description="分类名，同时默认作为文件夹名")
    keywords: List[str] = Field(default_factory=list, description="命中该分类的关键词")
    weight: float = Field(1.0, description="随机权重，>0 才会被选中")
    enabled: bool = Field(True, description="是否启用该分类")
    path: Optional[str] = Field(None, description="自定义存储子路径（默认使用分类名）")
    description: Optional[str] = Field(None, description="分类说明")

    @validator("weight", pre=True)
    def validate_weight(cls, value):
        try:
            value = float(value)
        except Exception:
            return 1.0
        return max(value, 0.0)


class EmoteConfig(BaseModel):
    """表情包全局配置"""

    enabled: bool = Field(True, description="是否开启表情包自动发送")
    send_probability: float = Field(0.25, description="单轮发送概率 0-1")
    base_path: str = Field("data/emotes", description="表情包根目录（分类子目录存放具体文件）")
    max_per_message: int = Field(1, description="单次最多附带多少张表情包")
    file_extensions: List[str] = Field(
        default_factory=lambda: ["png", "jpg", "jpeg", "gif", "webp"],
        description="允许的文件后缀",
    )
    categories: List[EmoteCategory] = Field(default_factory=list, description="分类列表")

    @validator("send_probability", pre=True)
    def clamp_probability(cls, value):
        try:
            value = float(value)
        except Exception:
            return 0.25
        return min(max(value, 0.0), 1.0)

    @validator("max_per_message", pre=True)
    def validate_max_per_message(cls, value):
        try:
            value = int(value)
        except Exception:
            return 1
        return max(1, value)
