from typing import Any

from mkmapdiary.lib.aiUsage import TAGS, TITLE, TRANSCRIPT
from mkmapdiary.tasks.siteTask import ai_disclosure_rows

STRINGS = {
    "ai_disclosure_titles": "Titles",
    "ai_disclosure_tags": "Tags",
    "ai_disclosure_transcripts": "Transcripts",
}

PROMPTS = {
    "generate_title": {"model": "title-model"},
    "generate_tags": {"model": "tags-model"},
}

ALL_ON: dict[str, Any] = {
    "llms": {"enabled": True},
    "transcription": {"enabled": True},
}


def _rows(
    used: set[str], features: dict[str, Any] | None = None
) -> list[dict[str, str]]:
    return ai_disclosure_rows(
        used,
        strings=STRINGS,
        prompts=PROMPTS,
        features=features if features is not None else ALL_ON,
        whisper_model="turbo",
    )


def test_no_rows_when_nothing_was_generated() -> None:
    """A photos-only trip built with every AI feature on claims nothing."""
    assert _rows(set()) == []


def test_titles_row_when_titles_were_generated() -> None:
    assert _rows({TITLE}) == [{"content": "Titles", "model": "title-model"}]


def test_tags_row_when_tags_were_generated() -> None:
    assert _rows({TAGS}) == [{"content": "Tags", "model": "tags-model"}]


def test_transcripts_row_when_audio_was_transcribed() -> None:
    assert _rows({TRANSCRIPT}) == [
        {"content": "Transcripts", "model": "whisper turbo"},
    ]


def test_every_row_when_everything_was_generated() -> None:
    assert _rows({TITLE, TAGS, TRANSCRIPT}) == [
        {"content": "Titles", "model": "title-model"},
        {"content": "Tags", "model": "tags-model"},
        {"content": "Transcripts", "model": "whisper turbo"},
    ]


def test_disabled_llms_drop_rows_recorded_by_an_earlier_build() -> None:
    """Records outlive the flag that produced them in a persistent build dir."""
    features: dict[str, Any] = {
        "llms": {"enabled": False},
        "transcription": {"enabled": True},
    }

    assert _rows({TITLE, TAGS, TRANSCRIPT}, features) == [
        {"content": "Transcripts", "model": "whisper turbo"},
    ]


def test_disabled_transcription_drops_a_recorded_transcript_row() -> None:
    features: dict[str, Any] = {
        "llms": {"enabled": True},
        "transcription": {"enabled": False},
    }

    assert _rows({TRANSCRIPT}, features) == []
