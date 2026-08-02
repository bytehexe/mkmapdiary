from typing import Any

from jinja2 import Environment, PackageLoader, StrictUndefined, select_autoescape

from mkmapdiary.lib.credits import Package

STRINGS = {
    "credits_title": "Credits",
    "credits_travellers": "Travellers",
    "credits_made_with": "Made with",
    "credits_software": "Open source software",
    "credits_toolchain": "Full list in the docs.",
}


def _render(**params: Any) -> str:
    env = Environment(
        loader=PackageLoader("mkmapdiary"),
        autoescape=select_autoescape(),
        undefined=StrictUndefined,
    )
    defaults: dict[str, Any] = {
        "travellers": [],
        "mkmapdiary_version": "1.2.3",
        "libraries": [],
        "docs_url": "https://bytehexe.github.io/mkmapdiary/reference/credits.html",
        "strings": STRINGS,
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
