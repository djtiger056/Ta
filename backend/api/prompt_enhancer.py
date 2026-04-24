from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.config import config as global_config
from backend.prompt_enhancer import get_enhancer
from backend.prompt_enhancer.config import IntentRule, PresetConfig, WordBankCategory, WordBankItem

router = APIRouter(prefix="/api/prompt-enhancer", tags=["Prompt Enhancer"])


class EnhanceRequest(BaseModel):
    prompt: str
    force_categories: Optional[List[str]] = None


class EnhanceResponse(BaseModel):
    original: str
    enhanced: str
    intents: Dict[str, bool]
    is_enhanced: bool


class SampleRequest(BaseModel):
    categories: List[str]
    pick_count: Optional[Dict[str, int]] = None


class ConfigUpdateRequest(BaseModel):
    enabled: Optional[bool] = None
    mode: Optional[str] = None
    categories: Optional[Dict[str, bool]] = None
    pick_count: Optional[Dict[str, int]] = None
    current_preset: Optional[str] = None
    allow_edit_builtin: Optional[bool] = None
    intents: Optional[List[IntentRule]] = None


class CategoryCreateRequest(BaseModel):
    path: str
    name: str
    items: Optional[List[str]] = None
    pick_count: Optional[int] = 1


class CategoryUpdateRequest(BaseModel):
    name: Optional[str] = None
    enabled: Optional[bool] = None
    pick_count: Optional[int] = None


class WordsRequest(BaseModel):
    category_path: str
    words: List[str]


class WordUpdateRequest(BaseModel):
    category_path: str
    word_index: int
    text: Optional[str] = None
    enabled: Optional[bool] = None
    weight: Optional[int] = None


class WordsDeleteRequest(BaseModel):
    category_path: str
    word_indices: List[int]


class PresetCreateRequest(BaseModel):
    name: str
    description: str
    outfit_style: str = "random"
    scene_type: str = "random"
    categories: Optional[List[str]] = None
    pick_count_overrides: Optional[Dict[str, int]] = None


class PresetUpdateRequest(BaseModel):
    description: Optional[str] = None
    outfit_style: Optional[str] = None
    scene_type: Optional[str] = None
    enabled: Optional[bool] = None
    categories: Optional[List[str]] = None
    pick_count_overrides: Optional[Dict[str, int]] = None


@router.post("/preview", response_model=EnhanceResponse)
async def preview_enhancement(request: EnhanceRequest):
    """预览增强效果"""
    enhancer = get_enhancer()
    return enhancer.get_enhancement_preview(request.prompt)


@router.post("/sample")
async def sample_words(request: SampleRequest):
    """按分类抽取词条，支持传入路径或大类关键字"""
    enhancer = get_enhancer()
    try:
        words = enhancer.sample_categories(request.categories, request.pick_count)
        merged = [word for items in words.values() for word in items]
        return {"words": words, "merged": "，".join(merged)}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/enhance", response_model=EnhanceResponse)
async def enhance_prompt(request: EnhanceRequest):
    """增强提示词"""
    enhancer = get_enhancer()
    return enhancer.get_enhancement_preview(request.prompt)


@router.get("/categories")
async def get_categories():
    """获取所有分类"""
    enhancer = get_enhancer()
    categories = enhancer.get_categories()
    return {"categories": [cat.dict() for cat in categories]}


@router.get("/categories/{path:path}")
async def get_category(path: str):
    """获取指定分类"""
    enhancer = get_enhancer()
    category = enhancer.get_category(path)
    if not category:
        raise HTTPException(status_code=404, detail=f"分类 '{path}' 不存在")
    return category.dict()


@router.post("/categories")
async def create_category(request: CategoryCreateRequest):
    """创建新分类"""
    enhancer = get_enhancer()
    try:
        category = enhancer.create_category(request.path, request.name, request.items, request.pick_count or 1)
        return {"message": "分类已创建", "category": category.dict()}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.put("/categories/{path:path}")
async def update_category(path: str, request: CategoryUpdateRequest):
    """更新分类"""
    enhancer = get_enhancer()
    try:
        updates = request.dict(exclude_none=True)
        category = enhancer.update_category(path, updates)
        return {"message": "分类已更新", "category": category.dict()}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.delete("/categories/{path:path}")
async def delete_category(path: str):
    """删除分类"""
    enhancer = get_enhancer()
    try:
        success = enhancer.delete_category(path)
        if success:
            return {"message": "分类已删除"}
        else:
            raise HTTPException(status_code=404, detail=f"分类 '{path}' 不存在")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/words")
async def add_words(request: WordsRequest):
    """添加词条"""
    enhancer = get_enhancer()
    try:
        items = enhancer.add_words(request.category_path, request.words)
        return {"message": "词条已添加", "items": [item.dict() for item in items]}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.put("/words")
async def update_word(request: WordUpdateRequest):
    """更新词条"""
    enhancer = get_enhancer()
    try:
        # 确保word_index是整数
        word_index = int(request.word_index) if isinstance(request.word_index, (int, str)) else request.word_index
        
        updates = request.dict(exclude_none=True, exclude={"category_path", "word_index"})
        if not updates:
            raise ValueError("没有提供要更新的字段")
        
        item = enhancer.update_word(request.category_path, word_index, updates)
        return {"message": "词条已更新", "item": item.dict()}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except IndexError as exc:
        raise HTTPException(status_code=404, detail=f"词条索引超出范围: {exc}")
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"更新词条失败: {str(exc)}")


@router.post("/words/delete")
async def delete_words(request: WordsDeleteRequest):
    """删除词条"""
    enhancer = get_enhancer()
    try:
        # 确保word_indices是整数列表
        word_indices = [int(idx) for idx in request.word_indices]
        
        if not word_indices:
            raise ValueError("没有提供要删除的词条索引")
        
        items = enhancer.delete_words(request.category_path, word_indices)
        return {"message": "词条已删除", "items": [item.dict() for item in items]}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"删除词条失败: {str(exc)}")


@router.get("/presets")
async def get_presets():
    """获取所有预设"""
    enhancer = get_enhancer()
    presets = enhancer.get_presets()
    return {"presets": [preset.dict() for preset in presets]}


@router.post("/presets")
async def create_preset(request: PresetCreateRequest):
    """创建新预设"""
    enhancer = get_enhancer()
    try:
        preset = enhancer.create_preset(
            request.name,
            request.description,
            request.outfit_style,
            request.scene_type,
            request.categories,
            request.pick_count_overrides
        )
        return {"message": "预设已创建", "preset": preset.dict()}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.put("/presets/{name}")
async def update_preset(name: str, request: PresetUpdateRequest):
    """更新预设"""
    enhancer = get_enhancer()
    try:
        updates = request.dict(exclude_none=True)
        preset = enhancer.update_preset(name, updates)
        return {"message": "预设已更新", "preset": preset.dict()}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.delete("/presets/{name}")
async def delete_preset(name: str):
    """删除预设"""
    enhancer = get_enhancer()
    try:
        success = enhancer.delete_preset(name)
        if success:
            return {"message": "预设已删除"}
        else:
            raise HTTPException(status_code=404, detail=f"预设 '{name}' 不存在")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.put("/presets/{name}/set-current")
async def set_current_preset(name: str):
    """设置当前预设"""
    enhancer = get_enhancer()
    try:
        preset = enhancer.set_current_preset(name)
        return {"message": "当前预设已设置", "preset": preset.dict()}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/config")
async def get_config():
    """获取当前增强配置"""
    enhancer = get_enhancer()
    return enhancer.config.dict()


@router.put("/config")
async def update_config(request: ConfigUpdateRequest):
    """更新增强配置并持久化"""
    enhancer = get_enhancer()
    updates = request.dict(exclude_none=True)
    updated_cfg = enhancer.update_config(updates)

    try:
        global_config.update_config("prompt_enhancer", updated_cfg.dict())
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"配置保存失败: {exc}")

    return {"message": "配置已更新", "config": updated_cfg.dict()}


@router.post("/reload")
async def reload_word_banks():
    """重新加载词库"""
    enhancer = get_enhancer()
    enhancer.reload_word_banks()
    return {"message": "词库已重新加载"}


# 兼容旧接口
@router.get("/word-banks")
async def get_word_banks():
    """获取词库内容（兼容旧接口）"""
    enhancer = get_enhancer()
    categories = enhancer.get_categories()
    
    # 转换为旧格式
    raw_data = {}
    tree_data = []
    
    for category in categories:
        # 构建嵌套数据结构
        parts = category.path.split(".")
        node = raw_data
        for part in parts:
            if part not in node:
                node[part] = {}
            node = node[part]
        
        # 设置词条列表
        if category.items:
            node[parts[-1]] = [item.text for item in category.items]
        
        # 构建扁平树
        tree_data.append({
            "path": category.path,
            "label": category.name,
            "words": [item.text for item in category.items],
            "count": len(category.items),
            "enabled": category.enabled,
            "pick_count": category.pick_count,
            "is_custom": not category.is_builtin
        })
    
    return {"raw": raw_data, "tree": tree_data}


@router.post("/word-banks/reload")
async def reload_word_banks_legacy():
    """重新加载词库（兼容旧接口）"""
    enhancer = get_enhancer()
    enhancer.reload_word_banks()
    return {"message": "词库已重新加载"}


@router.post("/word-banks/custom")
async def add_custom_words_legacy(request: WordsRequest):
    """添加自定义词条（兼容旧接口）"""
    enhancer = get_enhancer()
    try:
        items = enhancer.add_words(request.category_path, request.words)
        return {"message": "已添加", "added": [item.text for item in items], "config": enhancer.config.dict()}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.delete("/word-banks/custom")
async def delete_custom_words_legacy(request: WordsDeleteRequest):
    """删除自定义词条（兼容旧接口）"""
    enhancer = get_enhancer()
    try:
        items = enhancer.delete_words(request.category_path, request.word_indices)
        return {"message": "已删除", "removed": [item.text for item in items], "config": enhancer.config.dict()}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
