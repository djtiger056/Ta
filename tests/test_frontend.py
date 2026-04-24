import asyncio
import sys
import os
from tests._secrets import require_api_key
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from backend.core.bot import Bot
from backend.config import config

async def simulate_api_calls():
    """模拟前端API调用"""
    print("🧪 模拟前端API调用...")
    
    try:
        # 初始化Bot
        bot = Bot()
        
        # 模拟获取配置API
        print("📋 模拟获取配置API...")
        config_data = bot.get_image_gen_config()
        print(f"✅ 配置获取成功: {config_data}")
        
        # 模拟更新配置API
        print("🔄 模拟更新配置API...")
        new_config = {
            "enabled": True,
            "provider": "modelscope",
            "modelscope": {
                "api_key": require_api_key("MODELSCOPE_API_KEY", "前端图片生成测试"),
                "model": "Tongyi-MAI/Z-Image-Turbo",
                "timeout": 120
            },
            "trigger_keywords": ["画", "生成图片", "生图", "绘制", "创作"],
            "generating_message": "🎨 正在为你生成图片，请稍候...",
            "error_message": "😢 图片生成失败：{error}",
            "success_message": "✨ 图片已生成完成！"
        }
        
        bot.update_image_gen_config(new_config)
        print("✅ 配置更新成功")
        
        # 模拟测试连接API
        print("🔗 模拟测试连接API...")
        connected = await bot.test_image_gen_connection()
        print(f"✅ 连接测试结果: {connected}")
        
        # 模拟生成图像API
        print("🖼️ 模拟生成图像API...")
        test_prompt = "一只可爱的小猫咪在花园里玩耍"
        image_data = await bot.generate_image(test_prompt)
        
        if image_data:
            print(f"✅ 图像生成成功，大小: {len(image_data)} bytes")
            
            # 保存测试图片
            with open("test_frontend_image.jpg", "wb") as f:
                f.write(image_data)
            print("💾 测试图片已保存为 test_frontend_image.jpg")
        else:
            print("❌ 图像生成失败")
        
        # 模拟触发检测
        print("🔍 模拟触发检测...")
        test_messages = [
            "画一只可爱的小猫",
            "创作一幅美丽的风景画",
            "生成图片：星空下的城市",
            "今天天气真好",
            "帮我生图，主题是梦幻森林"
        ]
        
        for msg in test_messages:
            prompt = bot.should_generate_image(msg)
            if prompt:
                print(f"✅ 触发: '{msg}' -> 提示词: '{prompt}'")
            else:
                print(f"❌ 不触发: '{msg}'")
        
        print("✅ 前端API模拟测试完成")
        
    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(simulate_api_calls())
