"""The creator line on the three templates that carry asset metadata."""

from typing import Any

from jinja2 import Environment, PackageLoader, StrictUndefined, select_autoescape

STRINGS: dict[str, Any] = {
    "journal_title": "Journal",
    "gallery_title": "Gallery",
    "map_title": "Map",
    "overview_title": "Overview",
    "zoom_to_fit": "Zoom to fit",
    "download_gpx": "Download GPX",
    "legend_track": "Track",
    "legend_waypoints": "Waypoints",
    "legend_activity_areas": "Activity areas",
    "legend_journal_entries": "Journal entries",
    "include_duplicates": "Include duplicates",
    "include_low_quality": "Include low quality",
    "show_quality_icons": "Show quality icons",
    "quality_good": "Good",
    "quality_bad": "Bad",
    "quality_excellent": "Excellent",
    "quality_low_entropy": "Low entropy",
    "quality_duplicate": "Duplicate",
    "quality_canonical": "Canonical",
    "track_label": "Track",
    "track_distance": "Distance",
    "track_elevation_gain": "Gain",
    "track_elevation_loss": "Loss",
    "track_time_moving": "Moving",
    "track_total_time": "Total",
    "home_title": "Home",
}


def _env() -> Environment:
    return Environment(
        loader=PackageLoader("mkmapdiary"),
        autoescape=select_autoescape(),
        undefined=StrictUndefined,
    )


def _journal(**params: Any) -> str:
    asset: dict[str, Any] = {
        "id": 1,
        "type": "markdown",
        "path": "note.md",
        "time": "14:32",
        "timezone": "Europe/Paris",
        "latitude": None,
        "longitude": None,
        "location": None,
        "location_admin": None,
        "creator": "Bob",
    }
    asset.update(params.pop("asset", {}))
    defaults: dict[str, Any] = {
        "assets": [asset],
        "strings": STRINGS,
        "show_creators": True,
    }
    defaults.update(params)
    return _env().get_template("day_journal.j2").render(**defaults)


def test_journal_shows_the_creator_when_enabled() -> None:
    assert "Bob" in _journal()


def test_journal_hides_the_creator_when_disabled() -> None:
    """A journal with one uniform creator repeats a name that says nothing."""
    assert "Bob" not in _journal(show_creators=False)


def test_journal_renders_no_separator_for_an_unattributed_asset() -> None:
    """show_creators is journal-wide; individual assets may still have none."""
    output = _journal(asset={"creator": None})

    assert "iconoir-user" not in output


def test_journal_carries_no_ai_label() -> None:
    """Creator attribution is human authorship, not machine-generated output."""
    assert "ai-generated" not in _journal()


def _gallery_item(**params: Any) -> dict[str, Any]:
    class _Path:
        """Minimal stand-in for the PosixPath the real template receives."""

        name = "photo.jpg"

    item: dict[str, Any] = {
        "id": 1,
        "path": _Path(),
        "time": "14:32",
        "timezone": "Europe/Paris",
        "latitude": None,
        "longitude": None,
        "location": None,
        "location_admin": None,
        "creator": "Bob",
        "quality": 0.5,
        "entropy": 7.0,
        "is_duplicate": None,
    }
    item.update(params)
    return item


def _gallery(**params: Any) -> str:
    item = _gallery_item(**params.pop("item", {}))
    defaults: dict[str, Any] = {
        "gallery_items": [item],
        "geo_items": [],
        "gpx_data": None,
        "gpx_file": None,
        "track_statistics": None,
        "highlight_images": [],
        "has_bad_photos": False,
        "has_duplicates": False,
        "strings": STRINGS,
        "show_creators": True,
    }
    defaults.update(params)
    return _env().get_template("day_gallery.j2").render(**defaults)


def test_gallery_shows_the_creator_when_enabled() -> None:
    assert "Bob" in _gallery()


def test_gallery_hides_the_creator_when_disabled() -> None:
    """A gallery with one uniform creator repeats a name that says nothing."""
    assert "Bob" not in _gallery(show_creators=False)


def test_gallery_renders_no_separator_for_an_unattributed_asset() -> None:
    """show_creators is journal-wide; individual items may still have none."""
    output = _gallery(item={"creator": None})

    assert "iconoir-user" not in output


def test_gallery_carries_no_ai_label() -> None:
    """Creator attribution is human authorship, not machine-generated output."""
    assert "ai-generated" not in _gallery()


def _index(**params: Any) -> str:
    item = _gallery_item(**params.pop("item", {}))
    defaults: dict[str, Any] = {
        "gallery_images": [item],
        "map_images": [],
        "with_map": False,
        "gallery_rows": 1,
        "gpx_data": None,
        "track_statistics": None,
        "strings": STRINGS,
        "show_creators": True,
    }
    defaults.update(params)
    return _env().get_template("index.j2").render(**defaults)


def test_index_shows_the_creator_when_enabled() -> None:
    assert "Bob" in _index()


def test_index_hides_the_creator_when_disabled() -> None:
    """A journal with one uniform creator repeats a name that says nothing."""
    assert "Bob" not in _index(show_creators=False)


def test_index_renders_no_separator_for_an_unattributed_asset() -> None:
    """show_creators is journal-wide; individual items may still have none."""
    output = _index(item={"creator": None})

    assert "iconoir-user" not in output


def test_index_carries_no_ai_label() -> None:
    """Creator attribution is human authorship, not machine-generated output."""
    assert "ai-generated" not in _index()
