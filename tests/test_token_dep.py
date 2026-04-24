import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.api.deps import get_access_token


def test_get_access_token_from_query():
    assert get_access_token(authorization=None, token="q1") == "q1"


def test_get_access_token_from_bearer_header():
    assert get_access_token(authorization="Bearer abc123", token=None) == "abc123"


def test_get_access_token_empty_when_missing():
    assert get_access_token(authorization=None, token=None) == ""
