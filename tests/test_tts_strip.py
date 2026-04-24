import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.tts.manager import TTSManager


def _make_manager(partial_sentences: int) -> TTSManager:
    return TTSManager(
        {
            "enabled": True,
            "probability": 1.0,
            "voice_only_when_tts": True,
            "randomization": {
                "enabled": True,
                "full_probability": 0.0,
                "partial_probability": 1.0,
                "none_probability": 0.0,
                "min_partial_sentences": partial_sentences,
                "max_partial_sentences": partial_sentences,
            },
            "segment_config": {"enabled": False},
            "text_cleaning": {"enabled": False},
        }
    )


def test_strip_selected_tail_sentences():
    mgr = _make_manager(partial_sentences=2)
    text = "你好呀。吃的什么呀。你在哪呢？"

    selected = mgr.select_text_for_tts(text)
    remaining = mgr.get_remaining_text(text)

    assert selected == "吃的什么呀。你在哪呢？"
    assert remaining == "你好呀。"


if __name__ == "__main__":
    test_strip_selected_tail_sentences()
    print("✅ test_tts_strip passed")
