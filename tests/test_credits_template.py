from typing import Any

from jinja2 import Environment, PackageLoader, StrictUndefined, select_autoescape

from mkmapdiary.lib.credits import Package

STRINGS = {
    "credits_title": "Credits",
    "credits_travellers": "Travellers",
    "credits_creators": "Creators",
    "credits_made_with": "Made with",
    "credits_software": "Open source software",
    "credits_toolchain": "Full list in the docs.",
    "ai_disclosure_title": "AI-generated content",
    "ai_disclosure_intro": "Parts of this journal were generated automatically.",
    "ai_disclosure_content": "Content",
    "ai_disclosure_model": "Model",
}


def _render(**params: Any) -> str:
    env = Environment(
        loader=PackageLoader("mkmapdiary"),
        autoescape=select_autoescape(),
        undefined=StrictUndefined,
    )
    defaults: dict[str, Any] = {
        "travellers": [],
        "creators": [],
        "mkmapdiary_version": "1.2.3",
        "libraries": [],
        "docs_url": "https://bytehexe.github.io/mkmapdiary/reference/credits.html",
        "strings": STRINGS,
        "ai_disclosure": [],
    }
    defaults.update(params)
    return env.get_template("credits.j2").render(**defaults)


def test_renders_travellers() -> None:
    output = _render(travellers=["Janna Hopp", "Alex"])

    assert "Travellers" in output
    assert "Janna Hopp" in output
    assert "Alex" in output


def test_omits_travellers_section_when_empty() -> None:
    output = _render(travellers=[])

    assert "Travellers" not in output


def test_always_credits_mkmapdiary_and_its_license() -> None:
    output = _render()

    assert "mkmapdiary" in output
    assert "1.2.3" in output
    assert "PolyForm Noncommercial" in output


def test_renders_libraries_with_versions_and_licenses() -> None:
    output = _render(
        libraries=[
            Package("leaflet", "1.9.4", "BSD-2-Clause", "https://leafletjs.com/"),
            Package("jquery", "3.7.1", "MIT", None),
        ],
    )

    assert "leaflet" in output
    assert "1.9.4" in output
    assert "BSD-2-Clause" in output
    assert "https://leafletjs.com/" in output
    # a library without a homepage still appears
    assert "jquery" in output


def test_links_to_the_docs_for_the_toolchain() -> None:
    output = _render()

    assert "https://bytehexe.github.io/mkmapdiary/reference/credits.html" in output


def test_renders_missing_license_as_not_declared() -> None:
    output = _render(libraries=[Package("cuda-toolkit", "12.0", None, None)])

    assert "| cuda-toolkit | 12.0 | not declared |" in output


def test_renders_ai_disclosure_naming_each_model() -> None:
    output = _render(
        ai_disclosure=[
            {"content": "Entry titles", "model": "granite3.3:8b"},
            {"content": "Audio transcripts", "model": "whisper turbo"},
        ],
    )

    assert "AI-generated content" in output
    assert "Parts of this journal were generated automatically." in output
    assert "| Entry titles | granite3.3:8b |" in output
    assert "| Audio transcripts | whisper turbo |" in output


def test_omits_ai_disclosure_when_nothing_was_generated() -> None:
    """A build with every AI feature off must not claim it used AI."""
    output = _render(ai_disclosure=[])

    assert "AI-generated content" not in output
    assert "Parts of this journal were generated automatically." not in output


def test_renders_creators() -> None:
    output = _render(creators=["Bob Ross", "Janna Hopp"])

    assert "Creators" in output
    assert "Bob Ross" in output
    assert "Janna Hopp" in output


def test_omits_the_creators_section_when_empty() -> None:
    assert "Creators" not in _render(creators=[])


def test_creators_are_separate_from_travellers() -> None:
    """Who travelled and who authored are different claims."""
    output = _render(travellers=["Alex"], creators=["Bob"])

    assert "Travellers" in output
    assert "Creators" in output
