import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import asyncio
import pytest

from backend.user import user_manager


@pytest.mark.asyncio
async def test_get_or_create_user_by_qq_id_creates_config():
    await user_manager.init_db()
    user = await user_manager.get_or_create_user_by_qq_id("999001")
    assert user.qq_user_id == "999001"

    cfg = await user_manager.get_user_config_dict(user.id)
    assert isinstance(cfg, dict)

