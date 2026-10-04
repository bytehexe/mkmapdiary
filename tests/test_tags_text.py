from mkmapdiary.tasks.tagsTask import journal_text


def test_no_assets_yield_no_text() -> None:
    assert journal_text([]) == ""


def test_untranscribed_audio_stub_yields_no_text() -> None:
    """With features.transcription off the .md holds only its heading.

    Stripping the title line leaves a bare newline, which the old list-emptiness
    check read as content and sent to the model.
    """
    assert journal_text([("audio", "### Audio\n\n")]) == ""


def test_whitespace_only_markdown_yields_no_text() -> None:
    assert journal_text([("markdown", "   \n\n  \n")]) == ""


def test_empty_markdown_file_yields_no_text() -> None:
    assert journal_text([("markdown", "")]) == ""


def test_audio_transcript_drops_the_title_line() -> None:
    text = journal_text([("audio", "### Audio: Harbour\n\nWe walked to the pier.")])

    assert "###" not in text
    assert text == "We walked to the pier."


def test_markdown_fence_lines_are_dropped() -> None:
    text = journal_text([("markdown", "Before\n```\nfenced\n```\nAfter")])

    assert "```" not in text
    assert text == "Before\nfenced\nAfter"


def test_assets_are_joined_with_a_blank_line() -> None:
    text = journal_text([("markdown", "One"), ("markdown", "Two")])

    assert text == "One\n\nTwo"


def test_content_survives_alongside_an_empty_asset() -> None:
    text = journal_text([("audio", "### Audio\n\n"), ("markdown", "Real entry")])

    assert text.strip() == "Real entry"
