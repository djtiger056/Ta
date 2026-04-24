import logging
import random
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

import yaml

from .config import PromptEnhancerConfig, PresetConfig, WordBankCategory, WordBankItem

logger = logging.getLogger(__name__)

# 默认人像关键词（用于兼容旧逻辑）
DEFAULT_PORTRAIT_KEYWORDS = {
    "自拍", "人像", "照片", "美女", "美照", "靓照", "帅哥", "帅气", "帅照",
    "萌妹", "写真", "头像", "形象", "portrait", "selfie", "photo", "girl",
    "boy", "woman", "man", "ootd"
}

# 默认的内置类别顺序
DEFAULT_CATEGORY_ORDER = [
    "hairstyle",
    "facial_features", 
    "outfit",
    "pose",
    "expression",
    "scene",
    "lighting",
    "quality",
]


def _resolve_path(path: str) -> Path:
    """将相对路径转换为项目根目录下的绝对路径"""
    p = Path(path)
    if not p.is_absolute():
        project_root = Path(__file__).resolve().parents[2]
        return project_root / p
    return p


class PromptEnhancer:
    """提示词增强器：基于本地词库补充人像细节"""

    def __init__(self, config: Optional[PromptEnhancerConfig] = None):
        self.config = config or PromptEnhancerConfig()
        self._config_mtime: Optional[float] = None
        self.builtin_word_bank_path = _resolve_path(self.config.builtin_word_bank_path)
        self.custom_word_bank_path = _resolve_path(self.config.custom_word_bank_path)
        self._builtin_mtime: Optional[float] = None
        self._custom_mtime: Optional[float] = None
        
        self.builtin_word_banks: Dict[str, Any] = {}
        self.custom_word_banks: Dict[str, Any] = {}
        self.custom_category_paths: Set[str] = set()
        self.deleted_categories: Set[str] = set()
        self.word_banks: Dict[str, Any] = {}
        self.categories: Dict[str, WordBankCategory] = {}
        self.presets: List[PresetConfig] = self.config.presets.copy()
        
        self._load_word_banks()
        self._build_categories()

    def _maybe_reload_config(self):
        """若 config.yaml 已更新则自动热重载 prompt_enhancer 配置"""
        try:
            from backend.config import config as global_config
            config_path = global_config.config_path
        except Exception:
            return

        try:
            mtime = config_path.stat().st_mtime if config_path.exists() else None
        except Exception:
            return

        if mtime == self._config_mtime:
            return

        try:
            global_config.refresh_from_file()
            new_cfg = global_config.prompt_enhancer_config
        except Exception as exc:
            logger.debug("检测到配置变更但热重载失败: %s", exc)
            return

        self._config_mtime = mtime
        self.config = new_cfg
        self.presets = self.config.presets.copy()
        self.builtin_word_bank_path = _resolve_path(self.config.builtin_word_bank_path)
        self.custom_word_bank_path = _resolve_path(self.config.custom_word_bank_path)
        self._load_word_banks()

    def _load_word_banks(self):
        """加载内置与自定义词库"""
        self.deleted_categories.clear()
        self.custom_category_paths.clear()
        self.builtin_word_banks = {}
        self.custom_word_banks = {}
        merged: Dict[str, Any] = {}
        self._builtin_mtime = None
        self._custom_mtime = None
        
        # 加载内置词库
        if self.builtin_word_bank_path.exists():
            try:
                self._builtin_mtime = self.builtin_word_bank_path.stat().st_mtime
                with open(self.builtin_word_bank_path, "r", encoding="utf-8") as f:
                    self.builtin_word_banks = yaml.safe_load(f) or {}
                    merged = self._deep_merge(merged, self.builtin_word_banks)
                logger.info("加载内置词库: %s", self.builtin_word_bank_path.name)
            except Exception as exc:
                logger.error("加载内置词库失败 %s: %s", self.builtin_word_bank_path, exc)

        # 加载自定义词库
        if self.custom_word_bank_path.exists():
            try:
                self._custom_mtime = self.custom_word_bank_path.stat().st_mtime
                with open(self.custom_word_bank_path, "r", encoding="utf-8") as f:
                    self.custom_word_banks = yaml.safe_load(f) or {}
                    self._collect_deleted_markers(self.custom_word_banks, [])
                    self.custom_category_paths = self._collect_category_paths(self.custom_word_banks)
                    merged = self._deep_merge(merged, self.custom_word_banks)
                logger.info("加载自定义词库: %s", self.custom_word_bank_path.name)
            except Exception as exc:
                logger.error("加载自定义词库失败 %s: %s", self.custom_word_bank_path, exc)

        self.word_banks = merged
        # 重建分类
        self._build_categories()

    def _maybe_reload_word_banks(self):
        """若文件已更新则自动热重载"""
        self._maybe_reload_config()
        try:
            builtin_mtime = self.builtin_word_bank_path.stat().st_mtime if self.builtin_word_bank_path.exists() else None
            custom_mtime = self.custom_word_bank_path.stat().st_mtime if self.custom_word_bank_path.exists() else None
        except Exception:
            return

        if builtin_mtime != self._builtin_mtime or custom_mtime != self._custom_mtime:
            logger.info("检测到词库文件变更，自动重载")
            self._load_word_banks()

    def _build_categories(self):
        """构建分类结构"""
        self.categories.clear()
        
        def build_category(node: Any, path_parts: List[str]):
            if node is None:
                return

            if isinstance(node, list):
                path = ".".join(path_parts)
                name = path_parts[-1] if path_parts else path
                is_custom = path in self.custom_category_paths
                
                # 转换为WordBankItem列表
                items: List[WordBankItem] = []
                for word in node:
                    if isinstance(word, str):
                        items.append(WordBankItem(text=word, enabled=True, weight=1))
                    elif isinstance(word, dict):
                        items.append(WordBankItem(
                            text=word.get("text", ""),
                            enabled=word.get("enabled", True),
                            weight=word.get("weight", 1)
                        ))
                
                self.categories[path] = WordBankCategory(
                    path=path,
                    name=name,
                    enabled=self._get_config_value(self.config.categories, path, True),
                    pick_count=self._get_config_value(self.config.pick_count, path, 1),
                    items=items,
                    is_builtin=not is_custom
                )
            elif isinstance(node, dict):
                for key, value in node.items():
                    build_category(value, path_parts + [key])

        # 构建分类
        build_category(self.word_banks, [])
        
        # 从配置中加载自定义预设
        self.presets = self.config.presets.copy()

    def _collect_category_paths(self, node: Any, path_parts: Optional[List[str]] = None) -> Set[str]:
        """遍历词库收集叶子分类路径"""
        if path_parts is None:
            path_parts = []

        paths: Set[str] = set()
        if node is None:
            return paths

        if isinstance(node, list):
            paths.add(".".join(path_parts))
        elif isinstance(node, dict):
            for key, value in node.items():
                paths |= self._collect_category_paths(value, path_parts + [key])
        return paths

    def _collect_deleted_markers(self, node: Any, path_parts: List[str]):
        """记录自定义词库中的删除标记（值为 None）"""
        if node is None:
            if path_parts:
                self.deleted_categories.add(".".join(path_parts))
            return

        if isinstance(node, dict):
            for key, value in node.items():
                self._collect_deleted_markers(value, path_parts + [key])

    def _get_config_value(self, mapping: Dict[str, Any], path: str, default: Any):
        """从配置中查找与路径最匹配的值，支持向上回退"""
        parts = path.split(".")
        for i in range(len(parts), 0, -1):
            key = ".".join(parts[:i])
            if key in mapping:
                return mapping[key]
        # 兼容只配置了末级名称的场景（如 "hairstyle"）
        for part in reversed(parts):
            if part in mapping:
                return mapping[part]
        return default

    def _deep_merge(self, base: Dict[str, Any], new_data: Dict[str, Any]) -> Dict[str, Any]:
        """递归合并词库/配置"""
        merged = dict(base) if base else {}
        for key, value in (new_data or {}).items():
            if (
                key in merged
                and isinstance(merged[key], dict)
                and isinstance(value, dict)
            ):
                merged[key] = self._deep_merge(merged[key], value)
            else:
                merged[key] = value
        return merged

    def detect_intent(self, prompt: str) -> Dict[str, bool]:
        """检测提示词中的意图（支持多目的增强）"""
        prompt_lower = prompt.lower()

        # 基于配置的意图匹配
        intent_flags: Dict[str, bool] = {}
        for intent in self.config.intents or []:
            if not intent.enabled:
                intent_flags[intent.name] = False
                continue
            keywords = intent.keywords or []
            matched = any(
                (kw.lower() in prompt_lower) or (kw in prompt)
                for kw in keywords
            )
            intent_flags[intent.name] = matched

        # 兼容旧的人像检测结果
        default_portrait = intent_flags.get("portrait", False) or any(
            kw in prompt_lower or kw in prompt for kw in DEFAULT_PORTRAIT_KEYWORDS
        )

        intent_flags.update({
            "is_portrait": default_portrait,
            "has_outfit": any(
                kw in prompt_lower or kw in prompt
                for kw in ["穿", "穿搭", "穿着", "衣服", "outfit", "wear"]
            ),
            "has_hairstyle": any(
                kw in prompt_lower or kw in prompt for kw in ["发", "发型", "头发", "hair"]
            ),
            "has_scene": any(
                kw in prompt_lower or kw in prompt
                for kw in ["背景", "场景", "地点", "background", "scene"]
            ),
            "has_lighting": any(
                kw in prompt_lower or kw in prompt
                for kw in ["光", "灯光", "光线", "light"]
            ),
        })
        return intent_flags

    def _match_categories(self, key: str) -> List[WordBankCategory]:
        """根据关键字或路径匹配可用的分类"""
        matches: List[WordBankCategory] = []

        direct = self.categories.get(key)
        if direct:
            matches.append(direct)

        for path, category in self.categories.items():
            parts = path.split(".")
            if key in parts and category not in matches:
                matches.append(category)
        return matches

    def _select_category_for_key(
        self, key: str, preset_config: Optional[PresetConfig] = None
    ) -> Optional[WordBankCategory]:
        """根据请求的关键字/路径选择一个具体的叶子分类"""
        candidates = self._match_categories(key)
        if not candidates:
            return None

        # 针对穿搭和场景优先匹配预设风格
        if key == "outfit" and preset_config and preset_config.outfit_style != "random":
            styled = [
                c for c in candidates if f".{preset_config.outfit_style}" in c.path
            ]
            if styled:
                candidates = styled
        if key == "scene" and preset_config and preset_config.scene_type != "random":
            styled = [c for c in candidates if f".{preset_config.scene_type}" in c.path]
            if styled:
                candidates = styled

        # 优先返回精确匹配的分类
        for c in candidates:
            if c.path == key:
                return c
        return random.choice(candidates)

    def _get_current_preset_config(self) -> Optional[PresetConfig]:
        """获取当前预设配置"""
        for preset in self.presets:
            if preset.name == self.config.current_preset:
                return preset
        return None

    def _pick_random(self, category_path: str, category: WordBankCategory) -> Optional[str]:
        """从词库随机抽取词条"""
        if not category.enabled or not category.items:
            return None

        # 过滤启用的词条
        enabled_items = [item for item in category.items if item.enabled]
        if not enabled_items:
            return None

        # 根据权重选择
        weights = [item.weight for item in enabled_items]
        selected = random.choices(enabled_items, weights=weights, k=1)[0]
        return selected.text

    def enhance_prompt(self, user_prompt: str, force_categories: Optional[List[str]] = None) -> str:
        """增强用户提示词"""
        self._maybe_reload_word_banks()
        if not self.config.enabled:
            return user_prompt

        intents = self.detect_intent(user_prompt)
        matched_intents = [intent for intent in (self.config.intents or []) if intents.get(intent.name)]
        # 没有匹配的意图且非强制分类时直接返回原文，兼容旧逻辑
        if not matched_intents and not intents.get("is_portrait") and not force_categories:
            return user_prompt

        enhanced_parts = [user_prompt]
        preset_config = self._get_current_preset_config()
        preset_categories = (
            (preset_config.categories or []) if (preset_config and preset_config.enabled) else []
        )
        
        # 确定要增强的类别
        categories_to_add: List[str] = []
        pick_overrides: Dict[str, int] = {}
        
        if force_categories:
            categories_to_add = force_categories
        elif matched_intents:
            used_preset_for_portrait = False
            for intent in matched_intents:
                pick_overrides.update(intent.pick_count_overrides or {})
                if (
                    intent.name == "portrait"
                    and intents.get("is_portrait")
                    and preset_categories
                ):
                    for path in preset_categories:
                        if path not in categories_to_add:
                            categories_to_add.append(path)
                    pick_overrides.update(preset_config.pick_count_overrides or {})
                    used_preset_for_portrait = True
                else:
                    for path in intent.categories:
                        if path not in categories_to_add:
                            categories_to_add.append(path)

            # 兼容用户未配置/禁用了 portrait intent，但仍被旧关键词识别为人像
            if intents.get("is_portrait") and preset_categories and not used_preset_for_portrait:
                prepend = [path for path in preset_categories if path not in categories_to_add]
                if prepend:
                    categories_to_add = prepend + categories_to_add
                pick_overrides.update(preset_config.pick_count_overrides or {})
        elif intents.get("is_portrait") and preset_categories:
            categories_to_add = preset_categories
            pick_overrides.update(preset_config.pick_count_overrides or {})
        else:
            # 根据意图和预设确定类别
            if not intents["has_hairstyle"]:
                categories_to_add.append("hairstyle")
            if not intents["has_outfit"]:
                categories_to_add.append("outfit")
            
            categories_to_add.extend(["facial_features", "pose", "expression"])
            
            if not intents["has_scene"]:
                categories_to_add.append("scene")
            if not intents["has_lighting"]:
                categories_to_add.append("lighting")
            
            categories_to_add.append("quality_boost")

        # 处理每个类别
        requested_categories = categories_to_add
        for category_key in requested_categories:
            category = self._select_category_for_key(category_key, preset_config)
            if not category:
                continue

            pick_times = self._get_config_value(
                pick_overrides,
                category_key,
                category.pick_count,
            )
            pick_times = max(1, pick_times)
            for _ in range(pick_times):
                selected = self._pick_random(category.path, category)
                if selected:
                    enhanced_parts.append(selected)

        final_prompt = "，".join(enhanced_parts)
        return final_prompt

    def get_enhancement_preview(self, user_prompt: str) -> Dict[str, Any]:
        """获取增强预览数据"""
        self._maybe_reload_word_banks()
        intents = self.detect_intent(user_prompt)
        enhanced = self.enhance_prompt(user_prompt)

        return {
            "original": user_prompt,
            "enhanced": enhanced,
            "intents": intents,
            "is_enhanced": enhanced != user_prompt,
        }

    def sample_categories(
        self,
        category_paths: List[str],
        pick_count: Optional[Dict[str, int]] = None
    ) -> Dict[str, List[str]]:
        """根据指定分类抽取词条，支持传入分类路径或大类关键词"""
        self._maybe_reload_word_banks()
        pick_count = pick_count or {}
        preset_config = self._get_current_preset_config()
        results: Dict[str, List[str]] = {}

        for category_key in category_paths:
            category = self._select_category_for_key(category_key, preset_config)
            if not category:
                raise ValueError(f"分类 '{category_key}' 不存在")

            times = pick_count.get(category_key, pick_count.get(category.path, None)) if pick_count else None
            times = times or self._get_config_value(
                preset_config.pick_count_overrides if preset_config else {},
                category_key,
                category.pick_count,
            )
            times = max(1, times or 1)

            selections: List[str] = []
            for _ in range(times):
                word = self._pick_random(category.path, category)
                if word:
                    selections.append(word)
            results[category.path] = selections

        return results

    def reload_word_banks(self):
        """重新加载词库（支持热更新）"""
        self._load_word_banks()
        logger.info("词库已重新加载")

    # 词库管理方法
    def get_categories(self) -> List[WordBankCategory]:
        """获取所有分类"""
        self._maybe_reload_word_banks()
        return list(self.categories.values())

    def get_category(self, path: str) -> Optional[WordBankCategory]:
        """获取指定分类"""
        self._maybe_reload_word_banks()
        return self.categories.get(path)

    def create_category(self, path: str, name: str, items: List[str] = None, pick_count: int = 1) -> WordBankCategory:
        """创建新分类"""
        self._maybe_reload_word_banks()
        if path in self.categories:
            raise ValueError(f"分类 '{path}' 已存在")

        word_items = [WordBankItem(text=item, enabled=True, weight=1) for item in (items or [])]
        self.deleted_categories.discard(path)

        category = WordBankCategory(
            path=path,
            name=name,
            enabled=True,
            pick_count=pick_count or 1,
            items=word_items,
            is_builtin=False
        )
        
        self.categories[path] = category
        self._save_categories_to_file()
        return category

    def update_category(self, path: str, updates: Dict[str, Any]) -> WordBankCategory:
        """更新分类"""
        self._maybe_reload_word_banks()
        category = self.categories.get(path)
        if not category:
            raise ValueError(f"分类 '{path}' 不存在")
        
        # 检查是否允许编辑内置分类
        if category.is_builtin and not self.config.allow_edit_builtin:
            raise ValueError(f"不允许编辑内置分类 '{path}'")

        self._ensure_category_custom(category)
        
        # 更新属性
        for key, value in updates.items():
            if hasattr(category, key):
                setattr(category, key, value)
        
        self._save_categories_to_file()
        return category

    def delete_category(self, path: str) -> bool:
        """删除分类"""
        self._maybe_reload_word_banks()
        category = self.categories.get(path)
        if not category:
            return False
        
        # 检查是否允许删除内置分类
        if category.is_builtin and not self.config.allow_edit_builtin:
            raise ValueError(f"不允许删除内置分类 '{path}'")
        
        if category.is_builtin:
            self.deleted_categories.add(path)
        else:
            self.deleted_categories.discard(path)

        del self.categories[path]
        self._save_categories_to_file()
        return True

    def add_words(self, category_path: str, words: List[str]) -> List[WordBankItem]:
        """向分类添加词条"""
        self._maybe_reload_word_banks()
        category = self.categories.get(category_path)
        if not category:
            raise ValueError(f"分类 '{category_path}' 不存在")
        
        # 检查是否允许编辑内置分类
        if category.is_builtin and not self.config.allow_edit_builtin:
            raise ValueError(f"不允许编辑内置分类 '{category_path}'")

        self._ensure_category_custom(category)
        
        existing_texts = {item.text for item in category.items}
        added_items = []
        for word in words:
            word = word.strip()
            if not word:
                continue
            
            # 检查是否已存在
            if word not in existing_texts:
                item = WordBankItem(text=word, enabled=True, weight=1)
                category.items.append(item)
                added_items.append(item)
                existing_texts.add(word)
        
        self._save_categories_to_file()
        return added_items

    def update_word(self, category_path: str, word_index: int, updates: Dict[str, Any]) -> WordBankItem:
        """更新词条"""
        self._maybe_reload_word_banks()
        category = self.categories.get(category_path)
        if not category:
            raise ValueError(f"分类 '{category_path}' 不存在")
        
        # 检查是否允许编辑内置分类
        if category.is_builtin and not self.config.allow_edit_builtin:
            raise ValueError(f"不允许编辑内置分类 '{category_path}'")

        self._ensure_category_custom(category)
        
        if word_index < 0 or word_index >= len(category.items):
            raise IndexError(f"词条索引 {word_index} 超出范围")
        
        item = category.items[word_index]
        for key, value in updates.items():
            if hasattr(item, key):
                setattr(item, key, value)
        
        self._save_categories_to_file()
        return item

    def delete_words(self, category_path: str, word_indices: List[int]) -> List[WordBankItem]:
        """删除词条"""
        self._maybe_reload_word_banks()
        category = self.categories.get(category_path)
        if not category:
            raise ValueError(f"分类 '{category_path}' 不存在")
        
        # 检查是否允许编辑内置分类
        if category.is_builtin and not self.config.allow_edit_builtin:
            raise ValueError(f"不允许编辑内置分类 '{category_path}'")

        self._ensure_category_custom(category)
        
        # 按索引从大到小排序，避免删除时索引变化
        sorted_indices = sorted(word_indices, reverse=True)
        removed_items = []
        
        for index in sorted_indices:
            if 0 <= index < len(category.items):
                removed_items.append(category.items.pop(index))
        
        self._save_categories_to_file()
        return removed_items

    def _ensure_category_custom(self, category: WordBankCategory):
        """将内置分类标记为可持久化的自定义版本"""
        if category.is_builtin:
            category.is_builtin = False
        if category.path in self.deleted_categories:
            self.deleted_categories.discard(category.path)

    def _save_categories_to_file(self):
        """保存分类到自定义词库文件"""
        custom_data: Dict[str, Any] = {}
        
        # 只保存非内置分类（包括对内置分类的修改后版本）
        for category in self.categories.values():
            if not category.is_builtin:
                self._save_category_to_dict(custom_data, category)

        # 记录删除标记，确保重新加载时不会合并回内置分类
        for path in self.deleted_categories:
            self._set_nested_value(custom_data, path.split("."), None)
        
        # 确保目录存在
        self.custom_word_bank_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 保存到文件
        with open(self.custom_word_bank_path, "w", encoding="utf-8") as f:
            yaml.dump(custom_data, f, allow_unicode=True, sort_keys=False)

    def _save_category_to_dict(self, data: Dict[str, Any], category: WordBankCategory):
        """将分类保存到字典结构"""
        parts = category.path.split(".")
        node = data
        
        # 创建嵌套结构
        for part in parts[:-1]:
            node = node.setdefault(part, {})
        
        # 保存词条
        leaf_key = parts[-1]
        node[leaf_key] = [
            {
                "text": item.text,
                "enabled": item.enabled,
                "weight": item.weight
            } for item in category.items
        ]

    def _set_nested_value(self, data: Dict[str, Any], parts: List[str], value: Any):
        """在嵌套字典中设置值，用于记录删除标记"""
        node = data
        for part in parts[:-1]:
            node = node.setdefault(part, {})
        node[parts[-1]] = value

    # 预设管理方法
    def get_presets(self) -> List[PresetConfig]:
        """获取所有预设"""
        return self.presets.copy()

    def create_preset(
        self,
        name: str,
        description: str,
        outfit_style: str = "random",
        scene_type: str = "random",
        categories: Optional[List[str]] = None,
        pick_count_overrides: Optional[Dict[str, int]] = None,
    ) -> PresetConfig:
        """创建新预设"""
        # 检查名称是否已存在
        for preset in self.presets:
            if preset.name == name:
                raise ValueError(f"预设 '{name}' 已存在")

        preset = PresetConfig(
            name=name,
            description=description,
            outfit_style=outfit_style,
            scene_type=scene_type,
            enabled=True,
            categories=categories or [],
            pick_count_overrides=pick_count_overrides or {},
        )
        
        self.presets.append(preset)
        self._save_presets_to_config()
        return preset

    def update_preset(self, name: str, updates: Dict[str, Any]) -> PresetConfig:
        """更新预设"""
        for preset in self.presets:
            if preset.name == name:
                for key, value in updates.items():
                    if hasattr(preset, key):
                        setattr(preset, key, value)
                self._save_presets_to_config()
                return preset
        
        raise ValueError(f"预设 '{name}' 不存在")

    def delete_preset(self, name: str) -> bool:
        """删除预设"""
        for i, preset in enumerate(self.presets):
            if preset.name == name:
                # 不允许删除当前正在使用的预设
                if self.config.current_preset == name:
                    raise ValueError(f"不能删除当前正在使用的预设 '{name}'")
                
                del self.presets[i]
                self._save_presets_to_config()
                return True
        
        return False

    def set_current_preset(self, name: str) -> PresetConfig:
        """设置当前预设"""
        for preset in self.presets:
            if preset.name == name:
                self.config.current_preset = name
                self._save_presets_to_config()
                return preset
        
        raise ValueError(f"预设 '{name}' 不存在")

    def _save_presets_to_config(self):
        """保存预设到配置文件"""
        try:
            from backend.config import config as global_config
            global_config.update_config("prompt_enhancer", {
                "presets": [preset.dict() for preset in self.presets],
                "current_preset": self.config.current_preset
            })
        except Exception as exc:
            logger.error("保存预设配置失败: %s", exc)

    def update_config(self, updates: Dict[str, Any]):
        """更新配置并返回最新配置"""
        merged = self._deep_merge(self.config.dict(), updates)
        self.config = PromptEnhancerConfig(**merged)
        self.presets = self.config.presets.copy()
        self.reload_word_banks()
        return self.config


# 全局单例
_enhancer_instance: Optional[PromptEnhancer] = None


def get_enhancer(force_reload: bool = False) -> PromptEnhancer:
    """获取或创建全局增强器实例"""
    global _enhancer_instance
    if _enhancer_instance is None or force_reload:
        try:
            from backend.config import config as global_config
            enhancer_config = (
                global_config.prompt_enhancer_config
                if hasattr(global_config, "prompt_enhancer_config")
                else PromptEnhancerConfig()
            )
        except Exception:
            enhancer_config = PromptEnhancerConfig()

        _enhancer_instance = PromptEnhancer(enhancer_config)
    return _enhancer_instance
