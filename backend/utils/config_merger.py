"""配置合并工具类"""
import copy
from typing import Dict, Any, Optional


class ConfigMerger:
    """配置合并器，实现用户配置覆盖全局配置"""

    @staticmethod
    def deep_merge(target: Dict[str, Any], source: Dict[str, Any]) -> Dict[str, Any]:
        """深度合并两个字典，source 的值会覆盖 target 的值
        
        Args:
            target: 目标字典（全局配置）
            source: 源字典（用户配置）
            
        Returns:
            合并后的字典
        """
        result = copy.deepcopy(target)
        
        for key, value in source.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                # 递归合并嵌套字典
                result[key] = ConfigMerger.deep_merge(result[key], value)
            else:
                # 直接覆盖值
                result[key] = copy.deepcopy(value)
        
        return result

    @staticmethod
    def deep_merge_skip_empty(target: Dict[str, Any], source: Dict[str, Any]) -> Dict[str, Any]:
        """深度合并两个字典，但跳过“空值”覆盖。

        适用于“用户配置覆盖全局配置”的场景：用户在 UI 留空字段时，
        通常希望继续沿用全局默认值，而不是用空字符串/空对象把默认值抹掉。

        空值定义：None、""、{}、[]。
        """
        result = copy.deepcopy(target)

        for key, value in source.items():
            if value is None or value == "" or value == {} or value == []:
                continue

            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = ConfigMerger.deep_merge_skip_empty(result[key], value)
            else:
                result[key] = copy.deepcopy(value)

        return result
    
    @staticmethod
    def get_user_config(
        global_config: Dict[str, Any],
        user_config: Optional[Dict[str, Any]],
        *,
        skip_empty: bool = False,
    ) -> Dict[str, Any]:
        """获取合并后的用户配置
        
        Args:
            global_config: 全局配置
            user_config: 用户配置（可选）
            
        Returns:
            合并后的配置
        """
        if not user_config:
            return global_config

        if skip_empty:
            return ConfigMerger.deep_merge_skip_empty(global_config, user_config)

        return ConfigMerger.deep_merge(global_config, user_config)
    
    @staticmethod
    def get_system_prompt(
        global_prompt: str,
        user_prompt: Optional[str]
    ) -> str:
        """获取系统提示词
        
        Args:
            global_prompt: 全局系统提示词
            user_prompt: 用户自定义系统提示词
            
        Returns:
            系统提示词
        """
        if user_prompt:
            return user_prompt
        return global_prompt
    
    @staticmethod
    def get_llm_config(
        global_config: Dict[str, Any],
        user_config: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """获取 LLM 配置"""
        global_llm = global_config.get('llm', {})
        user_llm = user_config.get('llm', {}) if user_config else None
        
        return ConfigMerger.get_user_config(global_llm, user_llm)
    
    @staticmethod
    def get_tts_config(
        global_config: Dict[str, Any],
        user_config: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """获取 TTS 配置"""
        global_tts = global_config.get('tts', {})
        user_tts = user_config.get('tts', {}) if user_config else None
        
        return ConfigMerger.get_user_config(global_tts, user_tts)
    
    @staticmethod
    def get_image_gen_config(
        global_config: Dict[str, Any],
        user_config: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """获取图像生成配置"""
        global_image_gen = global_config.get('image_generation', {})
        user_image_gen = user_config.get('image_generation', {}) if user_config else None
        
        return ConfigMerger.get_user_config(global_image_gen, user_image_gen)
    
    @staticmethod
    def get_vision_config(
        global_config: Dict[str, Any],
        user_config: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """获取视觉识别配置"""
        global_vision = global_config.get('vision', {})
        user_vision = user_config.get('vision', {}) if user_config else None
        
        return ConfigMerger.get_user_config(global_vision, user_vision)
    
    @staticmethod
    def get_emote_config(
        global_config: Dict[str, Any],
        user_config: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """获取表情包配置"""
        global_emote = global_config.get('emotes', {})
        user_emote = user_config.get('emotes', {}) if user_config else None
        
        return ConfigMerger.get_user_config(global_emote, user_emote)


# 全局配置合并器实例
config_merger = ConfigMerger()
