import logging
from typing import Any

from mkmapdiary.lib.credits import Package
from mkmapdiary.tasks.siteTask import credits_libraries

SITE_CONFIG: dict[str, Any] = {
    "extra_css": [
        "extra.css",
        "https://unpkg.com/leaflet@1.9.4/dist/leaflet.css",
    ],
    "extra_javascript": [
        {"path": "https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"},
    ],
}


def test_merges_frontend_and_bundled_packages_sorted_case_insensitively() -> None:
    installed = {
        "mkdocs-material": Package("mkdocs-material", "9.5.0", "MIT", None),
        "mkdocs-glightbox": Package("mkdocs-glightbox", "0.5.2", "MIT", None),
    }

    libraries = credits_libraries(
        SITE_CONFIG,
        installed,
        ("mkdocs-material", "mkdocs-glightbox"),
    )

    names = [library.name for library in libraries]
    assert names == sorted(names, key=str.lower)
    assert "leaflet" in names
    assert "mkdocs-material" in names
    assert "mkdocs-glightbox" in names


def test_bundled_name_present_in_installed_contributes_its_package() -> None:
    installed = {
        "mkdocs-material": Package(
            "mkdocs-material",
            "9.5.0",
            "MIT",
            "https://squidfunk.github.io/mkdocs-material/",
        ),
    }

    libraries = credits_libraries({}, installed, ("mkdocs-material",))

    assert len(libraries) == 1
    package = libraries[0]
    assert package.name == "mkdocs-material"
    assert package.version == "9.5.0"
    assert package.license == "MIT"


def test_bundled_name_absent_from_installed_is_skipped_with_a_warning(
    caplog: Any,
) -> None:
    with caplog.at_level(logging.WARNING):
        libraries = credits_libraries({}, {}, ("mkdocs-material",))

    assert libraries == []
    assert any(
        record.levelno == logging.WARNING and "mkdocs-material" in record.getMessage()
        for record in caplog.records
    )


def test_empty_site_config_yields_only_bundled_packages() -> None:
    installed = {
        "mkdocs-material": Package("mkdocs-material", "9.5.0", "MIT", None),
    }

    libraries = credits_libraries({}, installed, ("mkdocs-material",))

    assert [library.name for library in libraries] == ["mkdocs-material"]


def test_missing_license_warns_with_the_package_name(caplog: Any) -> None:
    installed = {
        "mkdocs-material": Package("mkdocs-material", "9.5.0", None, None),
    }

    with caplog.at_level(logging.WARNING):
        libraries = credits_libraries({}, installed, ("mkdocs-material",))

    assert libraries[0].license is None
    assert any(
        record.levelno == logging.WARNING and "mkdocs-material" in record.getMessage()
        for record in caplog.records
    )
