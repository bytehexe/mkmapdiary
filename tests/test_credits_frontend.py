from pathlib import Path
from typing import Any

import yaml

from mkmapdiary.lib.credits import (
    FRONTEND_LICENSES,
    canonical_name,
    frontend_libraries,
    parse_cdn_url,
)

SITE_CONFIG = (
    Path(__file__).parent.parent
    / "src"
    / "mkmapdiary"
    / "resources"
    / "site_config.yaml"
)


def test_parse_unpkg() -> None:
    assert parse_cdn_url("https://unpkg.com/leaflet@1.9.4/dist/leaflet.js") == (
        "leaflet",
        "1.9.4",
    )


def test_parse_unpkg_scoped_package() -> None:
    url = "https://unpkg.com/@lychee-org/leaflet.photo@1.0.0/Leaflet.Photo.css"
    assert parse_cdn_url(url) == ("@lychee-org/leaflet.photo", "1.0.0")


def test_parse_cdnjs() -> None:
    url = "https://cdnjs.cloudflare.com/ajax/libs/jquery/3.7.1/jquery.min.js"
    assert parse_cdn_url(url) == ("jquery", "3.7.1")


def test_parse_jsdelivr_npm_without_version() -> None:
    url = "https://cdn.jsdelivr.net/npm/justifiedGallery/dist/css/justifiedGallery.min.css"
    assert parse_cdn_url(url) == ("justifiedGallery", None)


def test_parse_jsdelivr_github() -> None:
    url = "https://cdn.jsdelivr.net/gh/iconoir-icons/iconoir@main/css/iconoir.css"
    assert parse_cdn_url(url) == ("iconoir-icons/iconoir", "main")


def test_local_path_is_not_a_cdn_url() -> None:
    assert parse_cdn_url("geo.js") is None


def test_frontend_libraries_from_site_config() -> None:
    config: dict[str, Any] = yaml.safe_load(SITE_CONFIG.read_text())
    libraries = frontend_libraries(config)

    names = {canonical_name(library.name) for library in libraries}
    assert "leaflet" in names
    assert "jquery" in names
    # mkmapdiary's own assets are not third-party credits
    assert not any(library.name.endswith(".js") for library in libraries)

    leaflet = next(lib for lib in libraries if canonical_name(lib.name) == "leaflet")
    assert leaflet.version == "1.9.4"
    assert leaflet.license is not None


def test_every_cdn_library_has_a_license_entry() -> None:
    """Staleness gate: adding a CDN library without crediting it fails here."""
    config: dict[str, Any] = yaml.safe_load(SITE_CONFIG.read_text())

    missing = []
    for library in frontend_libraries(config):
        if canonical_name(library.name) not in FRONTEND_LICENSES:
            missing.append(library.name)

    assert not missing, (
        f"Add these to FRONTEND_LICENSES in mkmapdiary/lib/credits.py: {missing}"
    )
