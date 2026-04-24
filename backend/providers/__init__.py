from .base import BaseLLMProvider
from .openai_provider import OpenAIProvider

# 提供商注册表
PROVIDERS = {
    'openai': OpenAIProvider,
    'siliconflow': OpenAIProvider,  # SiliconFlow使用OpenAI兼容接口
    'deepseek': OpenAIProvider,     # DeepSeek使用OpenAI兼容接口
    'yunwu': OpenAIProvider,        # yunwu.ai使用OpenAI兼容接口
    'qwen': OpenAIProvider,         # 千问（DashScope）使用OpenAI兼容接口
}

def get_provider(provider_name: str, llm_config: dict | None = None) -> BaseLLMProvider:
    """获取LLM提供商实例"""
    if provider_name not in PROVIDERS:
        raise ValueError(f"不支持的LLM提供商: {provider_name}")
    return PROVIDERS[provider_name](provider_name, llm_config=llm_config)

__all__ = ['BaseLLMProvider', 'OpenAIProvider', 'get_provider']
