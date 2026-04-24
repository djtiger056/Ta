"""测试图片生成自动降级功能"""
import asyncio
import sys
import os
from tests._secrets import require_api_key

# 添加backend目录到Python路径
backend_path = os.path.join(os.path.dirname(__file__), '..', 'backend')
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

from image_gen.config import ImageGenerationConfig
from image_gen.manager import ImageGenerationManager


async def test_fallback():
    """测试自动降级功能"""
    print("=== 测试图片生成自动降级功能 ===\n")

    # 创建配置（使用魔搭社区作为主提供商，云舞作为备用）
    config = ImageGenerationConfig(
        enabled=True,
        provider="modelscope",
        fallback_provider="yunwu",
        enable_fallback=True,
        modelscope={
            "api_key": require_api_key("MODELSCOPE_API_KEY", "图片生成主提供商测试"),
            "model": "Tongyi-MAI/Z-Image-Turbo",
            "timeout": 120
        },
        yunwu={
            "api_key": require_api_key("YUNWU_API_KEY", "图片生成备用提供商测试"),
            "api_base": "https://yunwu.ai/v1",
            "model": "jimeng-4.5",
            "timeout": 120
        }
    )

    print("配置信息:")
    print(f"  主提供商: {config.provider}")
    print(f"  备用提供商: {config.fallback_provider}")
    print(f"  自动降级: {'启用' if config.enable_fallback else '禁用'}")
    print()

    # 创建管理器
    print("创建图片生成管理器...")
    manager = ImageGenerationManager(config)
    print("[OK] 管理器创建成功")
    print()

    # 测试生成图片
    print("测试生成图片...")
    prompt = "一只可爱的猫咪在阳光下睡觉"
    print(f"提示词: {prompt}")
    print()

    try:
        image_data = await manager.generate_image(prompt)

        if image_data:
            print(f"[OK] 图片生成成功！")
            print(f"  图片大小: {len(image_data)} bytes")
        else:
            print(f"[FAIL] 图片生成失败")
    except Exception as e:
        print(f"[FAIL] 生成过程中出错: {str(e)}")

    print("\n=== 测试完成 ===")


if __name__ == "__main__":
    asyncio.run(test_fallback())
