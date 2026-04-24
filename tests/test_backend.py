import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from backend.core.bot import Bot
from backend.config import config

async def test_backend():
    """测试后端核心功能"""
    print("🧪 测试后端核心功能...")
    
    try:
        # 测试配置加载
        print("📋 测试配置加载...")
        image_gen_config = config.image_gen_config
        print(f"✅ 配置加载成功: {image_gen_config.dict()}")
        
        # 测试Bot初始化
        print("🤖 测试Bot初始化...")
        bot = Bot()
        print("✅ Bot初始化成功")
        
        # 测试图像生成配置获取
        print("🖼️ 测试图像生成配置获取...")
        bot_config = bot.get_image_gen_config()
        print(f"✅ 配置获取成功: {bot_config}")
        
        # 测试触发检测
        print("🔍 测试触发检测...")
        test_messages = [
            "画一只可爱的小猫",
            "生成图片：美丽的风景",
            "帮我生图，主题是星空",
            "今天天气真不错",
            "绘制一座宏伟的城堡"
        ]
        
        for msg in test_messages:
            prompt = bot.should_generate_image(msg)
            if prompt:
                print(f"✅ 触发: '{msg}' -> 提示词: '{prompt}'")
            else:
                print(f"❌ 不触发: '{msg}'")
        
        # 测试图像生成
        print("🎨 测试图像生成...")
        test_prompt = "一只可爱的小猫咪在花园里玩耍"
        image_data = await bot.generate_image(test_prompt)
        
        if image_data:
            print(f"✅ 图像生成成功，大小: {len(image_data)} bytes")
            
            # 保存测试图片
            with open("test_backend_image.jpg", "wb") as f:
                f.write(image_data)
            print("💾 测试图片已保存为 test_backend_image.jpg")
        else:
            print("❌ 图像生成失败")
        
        # 测试连接
        print("🔗 测试连接...")
        connected = await bot.test_image_gen_connection()
        print(f"✅ 连接测试结果: {connected}")
        
    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_backend())