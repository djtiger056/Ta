import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.core.bot import Bot


def test_should_generate_image_uses_user_config_keywords():
    bot = Bot()

    # 仅给 u1 配置一个“全局不包含”的触发关键词
    bot._user_configs["u1"] = {
        "image_generation": {
            "enabled": True,
            "trigger_keywords": ["画图专用"],
        }
    }

    assert bot.should_generate_image("画图专用：一只猫", user_id="u1") == "一只猫"
    assert bot.should_generate_image("画图专用：一只猫", user_id="u2") is None

