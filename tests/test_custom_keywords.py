import asyncio
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from backend.core.bot import Bot
from backend.config import config

async def test_custom_keywords():
    """测试自定义关键词功能"""
    print("🧪 测试自定义关键词功能...")
    
    try:
        # 初始化Bot
        bot = Bot()
        
        # 获取原始配置
        original_config = bot.get_image_gen_config()
        original_keywords = original_config['trigger_keywords']
        print(f"📋 原始触发关键词: {original_keywords}")
        
        # 测试自定义关键词
        custom_keywords = ["画画", "图片", "AI绘图", "创作"]
        print(f"🔧 设置自定义关键词: {custom_keywords}")
        
        # 更新配置
        new_config = original_config.copy()
        new_config['trigger_keywords'] = custom_keywords
        bot.update_image_gen_config(new_config)
        
        # 验证配置是否更新
        updated_config = bot.get_image_gen_config()
        updated_keywords = updated_config['trigger_keywords']
        print(f"✅ 更新后的触发关键词: {updated_keywords}")
        
        # 测试新关键词是否生效
        test_messages = [
            ("画画一只可爱的小狗", True),
            ("帮我图片：美丽的风景", True),
            ("AI绘图，主题是星空", True),
            ("创作一幅抽象画", True),
            ("画一只小猫", False),  # 原关键词，现在应该不触发
            ("今天天气很好", False)
        ]
        
        print("🔍 测试新关键词触发效果:")
        for message, should_trigger in test_messages:
            prompt = bot.should_generate_image(message)
            triggered = prompt is not None
            
            if triggered == should_trigger:
                print(f"✅ 正确: '{message}' -> 触发={triggered}, 提示词='{prompt}'")
            else:
                print(f"❌ 错误: '{message}' -> 期望触发={should_trigger}, 实际触发={triggered}")
        
        # 恢复原始配置
        print("🔄 恢复原始配置...")
        bot.update_image_gen_config(original_config)
        
        # 验证配置文件是否正确更新
        print("📁 验证配置文件...")
        config_from_file = config.image_gen_config
        file_keywords = config_from_file.trigger_keywords
        print(f"📄 配置文件中的关键词: {file_keywords}")
        
        if set(file_keywords) == set(original_keywords):
            print("✅ 配置文件已正确恢复")
        else:
            print(f"❌ 配置文件恢复失败，期望: {original_keywords}, 实际: {file_keywords}")
        
        print("🎉 自定义关键词功能测试完成!")
        
    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_custom_keywords())