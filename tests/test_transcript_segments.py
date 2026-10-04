from mkmapdiary.tasks.audioTask import usable_segments


def _segment(start: float, end: float, text: str = "words") -> dict:
    return {"start": start, "end": end, "text": text}


def test_no_segments_yield_nothing() -> None:
    """Silent audio produces no transcript, so nothing to title either."""
    assert usable_segments([], 30.0) == []


def test_segments_within_the_audio_are_kept() -> None:
    segments = [_segment(0, 5), _segment(5, 10)]

    assert usable_segments(segments, 30.0) == segments


def test_a_segment_ending_exactly_at_the_end_is_kept() -> None:
    segments = [_segment(0, 30)]

    assert usable_segments(segments, 30.0) == segments


def test_segments_past_the_audio_end_are_dropped() -> None:
    """Whisper can hallucinate trailing segments once the audio has run out."""
    keep = _segment(0, 5)

    assert usable_segments([keep, _segment(5, 99)], 30.0) == [keep]


def test_everything_after_the_first_overrun_is_dropped() -> None:
    keep = _segment(0, 5)

    result = usable_segments([keep, _segment(5, 99), _segment(6, 7)], 30.0)

    assert result == [keep]
