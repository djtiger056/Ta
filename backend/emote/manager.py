import base64
import mimetypes
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from .models import EmoteCategory, EmoteConfig


@dataclass
class EmoteSelection:
    """一次命中的表情包信息"""

    category: str
    file_name: str
    file_path: str
    mime_type: str
    base64_data: str
    matched_keywords: List[str]

    def as_bytes(self) -> bytes:
        return base64.b64decode(self.base64_data)

    def to_public_dict(self) -> Dict[str, str]:
        return {
            "category": self.category,
            "file_name": self.file_name,
            "file_path": self.file_path,
            "mime_type": self.mime_type,
            "matched_keywords": self.matched_keywords,
            "data_url": f"data:{self.mime_type};base64,{self.base64_data}",
        }


class EmoteManager:
    """表情包发送与配置管理"""

    def __init__(self, config: EmoteConfig):
        self.config = config
        self.base_path = self._resolve_base_path(config.base_path)
        self._category_files: Dict[str, List[Path]] = {}
        self._category_paths: Dict[str, Path] = {}
        self.refresh_files()

    def _resolve_base_path(self, path: str) -> Path:
        """兼容不同环境的路径，盘符不合法时回退到默认值"""
        project_root = Path(__file__).resolve().parent.parent
        default_path = (project_root / "data" / "emotes").resolve()

        candidate = Path(path) if path else default_path
        if not candidate.is_absolute():
            candidate = (project_root / candidate).resolve()

        try:
            candidate.mkdir(parents=True, exist_ok=True)
            resolved = candidate
        except FileNotFoundError as e:
            print(f"[WARN] 表情包根路径 {candidate} 无法创建，回退使用 {default_path}: {e}")
            default_path.mkdir(parents=True, exist_ok=True)
            resolved = default_path

        self.config.base_path = str(resolved)
        return resolved

    def _category_path(self, category: EmoteCategory) -> Path:
        folder_name = category.path or category.name
        path = Path(folder_name)
        if path.is_absolute():
            return path
        return (self.base_path / folder_name).resolve()

    def refresh_files(self):
        """重新扫描文件目录"""
        self._category_files = {}
        self._category_paths = {}
        for category in self.config.categories:
            cat_path = self._category_path(category)
            try:
                cat_path.mkdir(parents=True, exist_ok=True)
            except FileNotFoundError as e:
                fallback = (self.base_path / Path(category.path or category.name).name).resolve()
                print(
                    f"[WARN] 表情包分类路径 {cat_path} 无法访问，回退使用 {fallback}: {e}"
                )
                fallback.mkdir(parents=True, exist_ok=True)
                cat_path = fallback

            self._category_paths[category.name] = cat_path
            files = []
            for ext in self.config.file_extensions:
                files.extend(cat_path.glob(f"*.{ext}"))
                files.extend(cat_path.glob(f"*.{ext.upper()}"))
            unique_files = []
            seen_paths = set()
            for file_path in files:
                resolved = file_path.resolve()
                if resolved in seen_paths:
                    continue
                seen_paths.add(resolved)
                unique_files.append(file_path)
            self._category_files[category.name] = sorted(unique_files)

    def list_categories_info(self) -> List[Dict[str, object]]:
        """返回分类的文件统计信息"""
        info = []
        for category in self.config.categories:
            files = self._category_files.get(category.name, [])
            cat_path = self._category_paths.get(category.name, self._category_path(category))
            info.append(
                {
                    "name": category.name,
                    "enabled": category.enabled,
                    "keywords": category.keywords,
                    "weight": category.weight,
                    "path": str(cat_path),
                    "file_count": len(files),
                    "sample_files": [f.name for f in files[:5]],
                }
            )
        return info

    def update_config(self, new_config: EmoteConfig):
        """更新配置并刷新扫描"""
        self.config = new_config
        self.base_path = self._resolve_base_path(new_config.base_path)
        self.refresh_files()

    def _pick_category(
        self, context_text: str
    ) -> Optional[Tuple[EmoteCategory, List[str]]]:
        """基于关键词和权重选择分类"""
        matched: List[tuple[EmoteCategory, List[str]]] = []
        candidates: List[EmoteCategory] = []

        for category in self.config.categories:
            if not category.enabled:
                continue
            files = self._category_files.get(category.name, [])
            if not files:
                continue
            if category.keywords:
                hit_keywords = [
                    kw for kw in category.keywords if kw and kw.lower() in context_text
                ]
                if hit_keywords:
                    matched.append((category, hit_keywords))
            else:
                candidates.append(category)

        # 有匹配的优先随机
        if matched:
            return random.choice(matched)

        if not candidates:
            return None

        weights = [max(cat.weight, 0.0) or 1.0 for cat in candidates]
        category = random.choices(candidates, weights=weights, k=1)[0]
        return category, []

    def select_emote(
        self, user_text: str, assistant_text: str
    ) -> Optional[EmoteSelection]:
        """根据概率与语境选取表情包"""
        if not self.config.enabled:
            return None
        if random.random() > self.config.send_probability:
            return None

        context_text = f"{user_text}\n{assistant_text}".lower()
        picked = self._pick_category(context_text)
        if not picked:
            return None
        category, hit_keywords = picked
        files = self._category_files.get(category.name, [])
        if not files:
            return None

        file_path = random.choice(files)
        mime_type, _ = mimetypes.guess_type(file_path.name)
        mime_type = mime_type or "image/png"

        try:
            data = file_path.read_bytes()
        except Exception:
            return None

        encoded = base64.b64encode(data).decode("utf-8")
        return EmoteSelection(
            category=category.name,
            file_name=file_path.name,
            file_path=str(file_path),
            mime_type=mime_type,
            base64_data=encoded,
            matched_keywords=hit_keywords,
        )
