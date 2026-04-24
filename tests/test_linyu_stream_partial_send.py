"""Linyu 流式发送的健壮性回归测试。"""

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

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest

from backend.adapters.linyu import LinyuAdapter


class _FakeBot:
    async def chat_stream(self, prompt, user_id=None, session_id=None):
        yield "第一句。"
        yield "第二句。"


@pytest.mark.asyncio
async def test_stream_partial_send_does_not_raise_on_late_send_failure():
    adapter = LinyuAdapter.__new__(LinyuAdapter)
    adapter.bot = _FakeBot()
    adapter.segment_enabled = False
    adapter.delay_range = [0.0, 0.0]

    sent_messages = []

    async def _fake_send_text_once(target_id, message, is_group=False, group_id=None):
        sent_messages.append(message)
        if len(sent_messages) == 2:
            raise RuntimeError("mock send failed")

    adapter._send_text_once = _fake_send_text_once
    adapter._extract_safe_stream_text = LinyuAdapter._extract_safe_stream_text.__get__(adapter, LinyuAdapter)
    adapter._split_ready_sentences = LinyuAdapter._split_ready_sentences.__get__(adapter, LinyuAdapter)
    adapter._split_incomplete_gen_img_prefix = LinyuAdapter._split_incomplete_gen_img_prefix.__get__(adapter, LinyuAdapter)

    result = await adapter._stream_reply_by_sentence("u1", "hi", session_id="u1")

    assert result == "第一句。第二句。"
    assert sent_messages[0] == "第一句。"


@pytest.mark.asyncio
async def test_stream_send_failure_before_any_sentence_should_raise():
    adapter = LinyuAdapter.__new__(LinyuAdapter)
    adapter.bot = _FakeBot()
    adapter.segment_enabled = False
    adapter.delay_range = [0.0, 0.0]

    async def _always_fail_send_text_once(target_id, message, is_group=False, group_id=None):
        raise RuntimeError("mock send failed immediately")

    adapter._send_text_once = _always_fail_send_text_once
    adapter._extract_safe_stream_text = LinyuAdapter._extract_safe_stream_text.__get__(adapter, LinyuAdapter)
    adapter._split_ready_sentences = LinyuAdapter._split_ready_sentences.__get__(adapter, LinyuAdapter)
    adapter._split_incomplete_gen_img_prefix = LinyuAdapter._split_incomplete_gen_img_prefix.__get__(adapter, LinyuAdapter)

    with pytest.raises(RuntimeError):
        await adapter._stream_reply_by_sentence("u1", "hi", session_id="u1")

