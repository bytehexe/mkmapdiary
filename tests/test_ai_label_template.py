"""The Art. 50 AI Act transparency marker (see CLAUDE.md "AI transparency").

The guard tests matter more than the happy paths: `BaseTask.ai()` returns an
empty string when `features.llms` is disabled, so a marker rendered
unconditionally would claim a model wrote text that no model touched.
"""

from typing import Any

from jinja2 import Environment, PackageLoader, StrictUndefined, select_autoescape

STRINGS = {
    "ai_generated_label": "AI-generated",
}


def _render(template: str, **params: Any) -> str:
    env = Environment(
        loader=PackageLoader("mkmapdiary"),
        autoescape=select_autoescape(),
        undefined=StrictUndefined,
    )
    return env.get_template(template).render(strings=STRINGS, **params)


def test_label_carries_the_eu_symbol_and_accessible_text() -> None:
    output = _render("ai_label.j2")

    assert 'src="ai-generated.svg"' in output
    assert 'alt="AI-generated"' in output
    assert "ai-generated-label" in output


def test_label_is_excluded_from_the_lightbox() -> None:
    """glightbox otherwise wraps it in an anchor, making the badge clickable."""
    assert "skip-lightbox" in _render("ai_label.j2")


def test_label_is_machine_readable_via_iptc_vocabulary() -> None:
    """The IPTC NewsCodes term for generative-AI output, as C2PA references it."""
    output = _render("ai_label.j2")

    assert (
        'data-digital-source-type="'
        'http://cv.iptc.org/newscodes/digitalsourcetype/trainedAlgorithmicMedia"'
    ) in output


def test_label_stays_on_one_line() -> None:
    """Audio headings are written as a single line and sliced as such."""
    assert "\n" not in _render("ai_label.j2")


def test_text_entry_title_is_labelled_when_ai_generated() -> None:
    output = _render("md_text.j2", title="Note: Fjord", text="body", ai_generated=True)

    assert "ai-generated.svg" in output
    assert "### Note: Fjord" in output


def test_text_entry_title_is_unlabelled_without_ai() -> None:
    output = _render("md_text.j2", title="Note", text="body", ai_generated=False)

    assert "ai-generated.svg" not in output
    assert "### Note" in output


def test_tags_are_labelled() -> None:
    output = _render("day_tags.j2", tags="hiking, fjord")

    assert "ai-generated.svg" in output
    assert "hiking, fjord" in output


def test_empty_tags_render_neither_block_nor_label() -> None:
    """`ai()` yields "" with LLMs off, which must drop the whole tags line."""
    output = _render("day_tags.j2", tags="")

    assert "ai-generated.svg" not in output
    assert "Tags:" not in output
