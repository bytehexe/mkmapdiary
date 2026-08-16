from typing import Any

from mkmapdiary.lib.asset import AssetRecord
from mkmapdiary.lib.calibration import Calibration, resolve

PARENT = Calibration(timezone="UTC", offset=0, effects=[], creator="Janna")


def test_creator_defaults_to_none() -> None:
    assert Calibration(timezone="UTC", offset=0).creator is None


def test_asset_record_carries_a_creator() -> None:
    from pathlib import PosixPath

    asset = AssetRecord(path=PosixPath("x.jpg"), type="image", creator="Bob")
    assert asset.creator == "Bob"
    assert AssetRecord(path=PosixPath("y.jpg"), type="image").creator is None


def test_omitted_creator_is_inherited() -> None:
    data: dict[str, Any] = {"calibration": {"timezone": "UTC", "offset": 0}}
    assert resolve(data, PARENT).creator == "Janna"


def test_creator_can_be_overridden() -> None:
    assert resolve({"creator": "Bob"}, PARENT).creator == "Bob"


def test_explicit_null_clears_an_inherited_creator() -> None:
    """Distinct from omitting the key, which inherits."""
    assert resolve({"creator": None}, PARENT).creator is None


def test_resolve_still_inherits_timezone_offset_and_effects() -> None:
    parent = Calibration(
        timezone="Europe/Berlin", offset=42, effects=["autorotate"], creator="Janna"
    )
    result = resolve({"creator": "Bob"}, parent)

    assert result.timezone == "Europe/Berlin"
    assert result.offset == 42
    assert result.effects == ["autorotate"]
