"""Highlights explicitly pinned in the configuration."""

import pathlib

import numpy as np
import pytest
import whenever

from mkmapdiary.lib.asset import AssetRecord
from mkmapdiary.lib.highlights import Highlights, resolve_pinned_highlights


def _asset(name: str, quality: float, minute: int = 0) -> AssetRecord:
    return AssetRecord(
        path=pathlib.Path(f"/assets/{name}.jpg"),
        type="image",
        timestamp_utc=whenever.Instant.from_utc(2026, 5, 1, 12, minute, 0),
        quality=quality,
        entropy=7.0,
    )


def test_pinned_asset_wins_its_cluster_over_a_better_one() -> None:
    """The point of pinning: the choice is the user's, not the quality score."""
    dull, sharp, other, spare = (
        _asset("dull", 0.1),
        _asset("sharp", 0.9),
        _asset("other", 0.5),
        _asset("spare", 0.4),
    )
    assets = [dull, sharp, other, spare]
    # dull/sharp sit together, other/spare sit together
    distances = np.array(
        [
            [0.0, 0.1, 1.0, 1.0],
            [0.1, 0.0, 1.0, 1.0],
            [1.0, 1.0, 0.0, 0.1],
            [1.0, 1.0, 0.1, 0.0],
        ]
    )

    selected = Highlights._cluster_assets(2, assets, distances, pinned=[dull])

    assert dull in selected
    assert sharp not in selected


def test_two_pins_in_one_cluster_cost_an_automatic_slot() -> None:
    """Pinning two similar pictures is allowed; the bucket may not grow for it."""
    first, second, tagalong = (
        _asset("first", 0.3),
        _asset("second", 0.4),
        _asset("tagalong", 0.9),
    )
    good, weak = _asset("good", 0.8), _asset("weak", 0.2)
    assets = [first, second, tagalong, good, weak]
    close, far = 0.1, 1.0
    distances = np.array(
        [
            [0.0, close, close, far, far],
            [close, 0.0, close, far, far],
            [close, close, 0.0, far, far],
            [far, far, far, 0.0, far],
            [far, far, far, far, 0.0],
        ]
    )

    selected = Highlights._cluster_assets(3, assets, distances, pinned=[first, second])

    assert first in selected
    assert second in selected
    assert len(selected) == 3
    assert weak not in selected, "the weakest automatic pick yields the slot"


def test_a_pinned_asset_survives_the_quality_filter() -> None:
    """An explicit choice outranks the heuristics that reject a picture."""
    blurry = _asset("blurry", 0.1, minute=1)
    blurry.is_bad = True
    blurry.entropy = 1.0
    rest = [_asset(f"rest{i}", 0.5, minute=i + 2) for i in range(3)]

    page = Highlights([blurry, *rest], {}, pinned=[blurry])

    assert blurry in page.gallery_assets


def test_pins_lead_the_gallery_in_configuration_order() -> None:
    """The list in the config is an order, not a set."""
    first, second = _asset("first", 0.2, minute=1), _asset("second", 0.3, minute=2)
    rest = [_asset(f"rest{i}", 0.9, minute=i + 3) for i in range(3)]

    page = Highlights([*rest, first, second], {}, pinned=[second, first])

    assert page.gallery_assets[:2] == [second, first]


def test_a_pinned_asset_is_not_spent_on_a_map_marker() -> None:
    """The pin belongs in the highlight strip; the map draws from the rest."""
    located = []
    for i in range(20):
        asset = _asset(f"geo{i}", 0.5, minute=i)
        asset.latitude, asset.longitude = 48.0 + i / 100, 11.0 + i / 100
        located.append(asset)
    pin = located[0]

    page = Highlights(located, {}, pinned=[pin])

    assert pin in page.gallery_assets
    assert pin not in page.map_assets


SOURCE_DIR = pathlib.Path("/journey")


def test_a_configured_path_resolves_to_the_converted_asset() -> None:
    """The config names the raw file; the page shows what it was converted to."""
    asset = _asset("IMG_1234", 0.5)
    sources = {asset.path: SOURCE_DIR / "day1" / "IMG_1234.CR2"}

    resolved = resolve_pinned_highlights(
        ["day1/IMG_1234.CR2"], SOURCE_DIR, [asset], sources.items()
    )

    assert resolved == [asset]


def test_an_unknown_path_stops_the_build() -> None:
    """A silently dropped highlight is worse than a loud failure."""
    asset = _asset("IMG_1234", 0.5)
    sources = {asset.path: SOURCE_DIR / "day1" / "IMG_1234.CR2"}

    with pytest.raises(ValueError, match="day1/nope.jpg"):
        resolve_pinned_highlights(
            ["day1/nope.jpg"], SOURCE_DIR, [asset], sources.items()
        )
