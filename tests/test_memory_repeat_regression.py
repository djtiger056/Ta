"""记忆重构后的复读回归测试。"""

import os
import sys
import types


if "chromadb" not in sys.modules:
    fake_chromadb = types.ModuleType("chromadb")
    fake_chromadb_config = types.ModuleType("chromadb.config")

    class _FakeSettings:
        pass

    fake_chromadb_config.Settings = _FakeSettings
    fake_chromadb.config = fake_chromadb_config
    sys.modules["chromadb"] = fake_chromadb
    sys.modules["chromadb.config"] = fake_chromadb_config

if "sentence_transformers" not in sys.modules:
    fake_st = types.ModuleType("sentence_transformers")

    class _FakeSentenceTransformer:
        def __init__(self, *args, **kwargs):
            pass

    fake_st.SentenceTransformer = _FakeSentenceTransformer
    sys.modules["sentence_transformers"] = fake_st

if "jwt" not in sys.modules:
    fake_jwt = types.ModuleType("jwt")

    class _FakeExpiredSignatureError(Exception):
        pass

    class _FakeInvalidTokenError(Exception):
        pass

    def _encode(payload, key, algorithm=None):
        return "fake-token"

    def _decode(token, key, algorithms=None):
        return {"user_id": 1, "username": "tester"}

    fake_jwt.encode = _encode
    fake_jwt.decode = _decode
    fake_jwt.ExpiredSignatureError = _FakeExpiredSignatureError
    fake_jwt.InvalidTokenError = _FakeInvalidTokenError
    sys.modules["jwt"] = fake_jwt

if "backend.user" not in sys.modules:
    fake_backend_user = types.ModuleType("backend.user")
    fake_backend_user.user_manager = object()
    sys.modules["backend.user"] = fake_backend_user

if "backend.user.manager" not in sys.modules:
    fake_backend_user_manager = types.ModuleType("backend.user.manager")
    fake_backend_user_manager.user_manager = object()
    sys.modules["backend.user.manager"] = fake_backend_user_manager

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from datetime import timedelta
import random

from backend.core.bot import Bot
from backend.utils.datetime_utils import get_now


def _make_bot() -> Bot:
    # 仅测试纯函数逻辑，避免触发完整初始化依赖
    return Bot.__new__(Bot)


def test_build_memory_context_deduplicates_recent_replies():
    bot = _make_bot()

    history = [
        {"role": "user", "content": "那你们多久放假呀"},
        {"role": "assistant", "content": "我们还得过几天才放假"},
    ]
    relevant_memories = [
        {"content": "我们还得过几天才放假", "similarity": 0.93},
        {"content": "你们晚上约了打王者", "similarity": 0.81},
        {"content": "你们晚上约了打王者", "similarity": 0.79},
    ]

    context = bot._build_memory_context(relevant_memories, history, limit=3)

    assert "过几天才放假" not in context
    assert context.count("你们晚上约了打王者") == 1
    assert "不要逐条回答、不要复述原句" in context


def test_long_gap_repeat_hint_triggers_for_same_question():
    bot = _make_bot()
    now = get_now()
    old_ts = (now - timedelta(minutes=70)).isoformat()
    history = [
        {"role": "user", "content": "在干嘛呀宝宝", "timestamp": old_ts},
        {"role": "assistant", "content": "在床上刷视频呢", "timestamp": old_ts},
    ]

    hint = bot._build_long_gap_repeat_hint(history, "在干嘛呀")
    assert "间隔约" in hint
    assert "新的时间点" in hint


def test_long_gap_repeat_hint_not_triggered_for_short_gap():
    bot = _make_bot()
    now = get_now()
    recent_ts = (now - timedelta(minutes=10)).isoformat()
    history = [
        {"role": "user", "content": "在干嘛呀", "timestamp": recent_ts},
    ]

    hint = bot._build_long_gap_repeat_hint(history, "在干嘛呀")
    assert hint == ""


def test_companion_mode_hint_can_generate_statement_end():
    bot = _make_bot()
    bot._session_last_companion_hint_turn = {}

    history = [
        {"role": "system", "content": "sys"},
        {"role": "user", "content": "学习得怎么样了呀"},
        {"role": "assistant", "content": "有点困"},
    ]

    old_random = random.random
    seq = iter([0.1, 0.1, 0.1])

    def _mock_random():
        return next(seq)

    random.random = _mock_random
    try:
        hint = bot._build_companion_mode_hint("s1", history, "你今天咋样")
    finally:
        random.random = old_random

    assert "近况/想法/情绪" in hint
    assert "关系里的真实感受" in hint
    assert "陈述句收尾" in hint
