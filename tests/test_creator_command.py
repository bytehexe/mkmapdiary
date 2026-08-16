from pathlib import Path
from typing import Any

import yaml
from click.testing import CliRunner

from mkmapdiary.commands.calibrate import calibrate


def _run(*args: str) -> Any:
    return CliRunner().invoke(calibrate, ["creator", *args])


def test_writes_a_creator_into_a_new_file(tmp_path: Path) -> None:
    result = _run("-o", str(tmp_path), "Bob Ross")

    assert result.exit_code == 0
    written = yaml.safe_load((tmp_path / "calibration.yaml").read_text())
    assert written["creator"] == "Bob Ross"


def test_preserves_existing_calibration_keys(tmp_path: Path) -> None:
    """The merge in write_calibration_data must not drop timezone/offset."""
    target = tmp_path / "calibration.yaml"
    target.write_text(
        yaml.safe_dump(
            {
                "calibration": {"timezone": "UTC", "offset": 42},
                "effects": ["autorotate"],
            }
        )
    )

    assert _run("-o", str(target), "Bob Ross").exit_code == 0

    written = yaml.safe_load(target.read_text())
    assert written["creator"] == "Bob Ross"
    assert written["calibration"] == {"timezone": "UTC", "offset": 42}
    assert written["effects"] == ["autorotate"]


def test_unset_writes_an_explicit_null(tmp_path: Path) -> None:
    """Null clears an inherited creator; omitting the key would inherit it."""
    assert _run("-o", str(tmp_path), "--unset").exit_code == 0

    written = yaml.safe_load((tmp_path / "calibration.yaml").read_text())
    assert "creator" in written
    assert written["creator"] is None


def test_name_and_unset_together_is_an_error(tmp_path: Path) -> None:
    result = _run("-o", str(tmp_path), "--unset", "Bob Ross")

    assert result.exit_code != 0
    assert not (tmp_path / "calibration.yaml").exists()


def test_neither_name_nor_unset_is_an_error(tmp_path: Path) -> None:
    result = _run("-o", str(tmp_path))

    assert result.exit_code != 0
    assert not (tmp_path / "calibration.yaml").exists()


def test_dry_run_writes_nothing(tmp_path: Path) -> None:
    assert _run("-o", str(tmp_path), "-n", "Bob Ross").exit_code == 0
    assert not (tmp_path / "calibration.yaml").exists()
