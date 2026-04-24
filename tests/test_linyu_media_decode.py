"""Linyu 媒体下载与解码回归测试。"""

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

from backend.adapters.linyu import LinyuAdapter
from backend.vision.providers.modelscope_vision import ModelScopeVisionProvider


def test_decode_base64_media_with_data_url_png():
    adapter = LinyuAdapter.__new__(LinyuAdapter)
    png_1x1 = (
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR4nGNgYAAAAAMA"
        "ASsJTYQAAAAASUVORK5CYII="
    )
    data_url = f"data:image/png;base64,{png_1x1}"

    decoded = adapter._decode_base64_media(data_url)

    assert decoded is not None
    assert decoded.startswith(b"\x89PNG\r\n\x1a\n")


def test_detect_image_mime_for_png_bytes():
    png_1x1 = bytes.fromhex(
        "89504E470D0A1A0A0000000D4948445200000001000000010804000000B51C0C02"
    )
    mime = ModelScopeVisionProvider._detect_image_mime(png_1x1)
    assert mime == "image/png"


def test_collect_media_message_ids_from_nested_payload():
    adapter = LinyuAdapter.__new__(LinyuAdapter)
    payload = {
        "id": "a1",
        "meta": {
            "msgId": "b2",
            "items": [
                {"mediaId": "c3"},
                {"file_id": "d4"},
            ]
        }
    }

    ids = adapter._collect_media_message_ids("root", payload)

    assert ids == ["root", "a1", "b2", "c3", "d4"]


def test_extract_media_payload_candidate_ignores_plain_non_media_text():
    adapter = LinyuAdapter.__new__(LinyuAdapter)
    payload = {"type": "img", "content": "just words"}

    candidate = adapter._extract_media_payload_candidate(payload)

    assert candidate is None


def test_is_likely_media_locator_accepts_base64_and_url():
    adapter = LinyuAdapter.__new__(LinyuAdapter)
    assert adapter._is_likely_media_locator("https://a.com/x.png")
    assert adapter._is_likely_media_locator("/v1/api/message/get/file/123")
    assert adapter._is_likely_media_locator("base64://aGVsbG8=")
    assert not adapter._is_likely_media_locator("img")


def test_extract_user_file_reference_from_file_name_path():
    adapter = LinyuAdapter.__new__(LinyuAdapter)
    payload = {
        "name": "image_cropper.jpg",
        "fileName": "76e723e9-49dc-4758-a953-b4fb4e729579/645d8dab-fecc-4c16-a57f-1ea6a.jpg",
    }

    target_id, file_name = adapter._extract_user_file_reference(payload)

    assert target_id == "76e723e9-49dc-4758-a953-b4fb4e729579"
    assert file_name == "645d8dab-fecc-4c16-a57f-1ea6a.jpg"


def test_media_retry_config_supports_independent_media_config():
    adapter = LinyuAdapter.__new__(LinyuAdapter)
    adapter.media_config = {
        "fetch_retry_count": 6,
        "fetch_retry_delay": 0.8,
        "debug_logs": False,
    }
    adapter.segment_config = {
        "media_fetch_retry_count": 6,
        "media_fetch_retry_delay": 0.8,
    }
    adapter.media_fetch_retry_count = int(
        adapter.media_config.get("fetch_retry_count", adapter.segment_config.get("media_fetch_retry_count", 4))
    )
    adapter.media_fetch_retry_delay = float(
        adapter.media_config.get("fetch_retry_delay", adapter.segment_config.get("media_fetch_retry_delay", 0.8))
    )
    adapter.media_debug_logs = bool(adapter.media_config.get("debug_logs", False))

    assert adapter.media_fetch_retry_count == 6
    assert adapter.media_fetch_retry_delay == 0.8
    assert adapter.media_debug_logs is False


def test_mask_ws_url_hides_token_content():
    adapter = LinyuAdapter.__new__(LinyuAdapter)
    masked = adapter._mask_ws_url("ws://127.0.0.1/ws?x-token=abcdefghijklmnopqrstuvwxyz123456")

    assert "x-token=" in masked
    assert "abcdefghijklmnopqrstuvwxyz123456" not in masked
