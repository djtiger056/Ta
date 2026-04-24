import asyncio
import sys
import os

# 添加backend目录到Python路径
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from image_gen import ImageGenerationManager, ImageGenerationConfig
from config import config


async def test_image_generation():
    """测试图像生成功能"""
    print("🎨 开始测试图像生成功能...")
    
    # 获取配置
    image_gen_config = config.image_gen_config
    print(f"📋 当前配置: {image_gen_config.dict()}")
    
    # 创建管理器
    manager = ImageGenerationManager(image_gen_config)
    
    # 测试连接
    print("🔗 测试API连接...")
    connected = await manager.test_connection()
    if connected:
        print("✅ API连接成功")
    else:
        print("❌ API连接失败")
        return
    
    # 测试触发检测
    test_messages = [
        "画一只可爱的小猫",
        "生成图片：美丽的风景",
        "帮我生图，主题是星空",
        "今天天气真不错",
        "绘制一座宏伟的城堡"
    ]
    
    print("\n🧪 测试触发关键词检测...")
    for msg in test_messages:
        prompt = manager.should_trigger_image_generation(msg)
        if prompt:
            print(f"✅ 触发: '{msg}' -> 提示词: '{prompt}'")
        else:
            print(f"❌ 不触发: '{msg}'")
    
    # 测试图像生成
    print("\n🖼️ 测试图像生成...")
    test_prompt = "一只可爱的小猫咪在花园里玩耍"
    print(f"📝 提示词: {test_prompt}")
    
    image_data = await manager.generate_image(test_prompt)
    if image_data:
        print(f"✅ 图像生成成功，大小: {len(image_data)} bytes")
        
        # 保存测试图片
        with open("test_image.jpg", "wb") as f:
            f.write(image_data)
        print("💾 测试图片已保存为 test_image.jpg")
    else:
        print("❌ 图像生成失败")


if __name__ == "__main__":
    asyncio.run(test_image_generation())