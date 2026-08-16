from collections.abc import Iterator
from datetime import date
from pathlib import Path
from typing import Any

import pytest
import yaml
from click.testing import CliRunner

from mkmapdiary.commands.config import config
from mkmapdiary.commands.params import PARAM_EXAMPLES
from mkmapdiary.lib.config import load_config_data


@pytest.fixture(autouse=True)
def isolated_environment(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> Iterator[Path]:
    """Keep the user config layer and the locale out of the developer's home.

    ``--get`` merges the real user config file and auto-detects the locale,
    so both are pinned here to make the dumped configuration deterministic.
    """
    user_config_dir = tmp_path / "userconfig"
    monkeypatch.setenv("XDG_CONFIG_HOME", str(user_config_dir))
    monkeypatch.setenv("LC_ALL", "en_US.UTF-8")
    yield user_config_dir / "mkmapdiary"


def _get(*args: str) -> Any:
    return CliRunner().invoke(config, ["--get", *args])


def _parse(result: Any) -> dict[str, Any]:
    assert result.exit_code == 0, result.output
    parsed = yaml.safe_load(result.stdout)
    assert isinstance(parsed, dict)
    return parsed


def test_get_prints_the_defaults(tmp_path: Path) -> None:
    parsed = _parse(_get(str(tmp_path)))

    assert parsed["site"]["image_format"] == "jpg"
    assert parsed["features"]["poi_detection"]["enabled"] is False


def test_get_resolves_auto_and_tagged_values(tmp_path: Path) -> None:
    """!auto, !duration and !distance are computed away, not dumped as tags."""
    parsed = _parse(_get(str(tmp_path)))

    assert parsed["site"]["locale"] == "en_US.UTF-8"
    assert isinstance(parsed["site"]["timezone"], str)
    assert parsed["features"]["geo_correlation"]["max_time_diff"] == 300


def test_get_fills_in_the_translated_strings(tmp_path: Path) -> None:
    parsed = _parse(_get(str(tmp_path)))

    assert parsed["strings"]
    assert all(isinstance(value, str) for value in parsed["strings"].values())


def test_get_output_is_a_valid_configuration(tmp_path: Path) -> None:
    """The dump can be fed back in as a config.yaml."""
    parsed = _parse(_get(str(tmp_path)))

    load_config_data(parsed)


def test_get_applies_params(tmp_path: Path) -> None:
    parsed = _parse(_get("-x", "site.image_format=webp", str(tmp_path)))

    assert parsed["site"]["image_format"] == "webp"


def test_get_includes_the_project_config(tmp_path: Path) -> None:
    (tmp_path / "config.yaml").write_text(
        yaml.safe_dump({"credits": {"travellers": ["Bob Ross"]}})
    )

    parsed = _parse(_get(str(tmp_path)))

    assert parsed["credits"]["travellers"] == ["Bob Ross"]


def test_params_win_over_the_project_config(tmp_path: Path) -> None:
    (tmp_path / "config.yaml").write_text(
        yaml.safe_dump({"site": {"image_format": "png"}})
    )

    parsed = _parse(_get("-x", "site.image_format=webp", str(tmp_path)))

    assert parsed["site"]["image_format"] == "webp"


def test_a_param_value_is_parsed_as_yaml_not_as_a_string(tmp_path: Path) -> None:
    parsed = _parse(_get("-x", "features.llms.enabled=no", str(tmp_path)))

    assert parsed["features"]["llms"]["enabled"] is False


def test_a_param_can_carry_a_list(tmp_path: Path) -> None:
    parsed = _parse(_get("-x", 'credits.travellers=["Bob Ross", "Ada"]', str(tmp_path)))

    assert parsed["credits"]["travellers"] == ["Bob Ross", "Ada"]


def test_a_param_can_carry_a_mapping(tmp_path: Path) -> None:
    parsed = _parse(
        _get("-x", "site.image_options={quality: 80, optimize: true}", str(tmp_path))
    )

    assert parsed["site"]["image_options"] == {"quality": 80, "optimize": True}


def test_a_param_can_carry_dates(tmp_path: Path) -> None:
    parsed = _parse(_get("-x", "ignore_dates=[2020-01-01]", str(tmp_path)))

    assert parsed["ignore_dates"] == [date(2020, 1, 1)]


def test_a_param_can_carry_null(tmp_path: Path) -> None:
    parsed = _parse(
        _get("-x", "features.poi_detection.connection.password=null", str(tmp_path))
    )

    assert parsed["features"]["poi_detection"]["connection"]["password"] is None


def test_a_param_can_use_the_duration_tag(tmp_path: Path) -> None:
    parsed = _parse(
        _get(
            "-x",
            "features.geo_correlation.max_time_diff=!duration 5 minutes",
            str(tmp_path),
        )
    )

    assert parsed["features"]["geo_correlation"]["max_time_diff"] == 300


def test_a_param_can_use_the_distance_tag(tmp_path: Path) -> None:
    parsed = _parse(
        _get(
            "-x",
            "features.track_simplification.tolerance=!distance 2.5 km",
            str(tmp_path),
        )
    )

    assert parsed["features"]["track_simplification"]["tolerance"] == 2500.0


def test_a_param_can_use_the_auto_tag(tmp_path: Path) -> None:
    parsed = _parse(_get("-x", "site.locale=!auto", str(tmp_path)))

    assert parsed["site"]["locale"] == "en_US.UTF-8"


def test_a_param_value_containing_an_equals_sign_is_kept_whole(
    tmp_path: Path,
) -> None:
    parsed = _parse(
        _get("-x", "features.poi_detection.connection.password=a=b", str(tmp_path))
    )

    assert parsed["features"]["poi_detection"]["connection"]["password"] == "a=b"


def test_a_param_without_an_equals_sign_is_rejected(tmp_path: Path) -> None:
    assert _get("-x", "site.image_format", str(tmp_path)).exit_code != 0


def test_a_param_is_validated_against_the_schema(tmp_path: Path) -> None:
    """`features.transcription` is an object, so a bare boolean must not pass."""
    assert _get("-x", "features.transcription=False", str(tmp_path)).exit_code != 0


@pytest.mark.parametrize("example", PARAM_EXAMPLES)
def test_the_documented_param_examples_work(example: str, tmp_path: Path) -> None:
    """The --help examples are the source of this list, so they cannot rot."""
    assert _get("-x", example, str(tmp_path)).exit_code == 0


def test_get_writes_nothing(tmp_path: Path) -> None:
    assert _get("-x", "site.image_format=webp", str(tmp_path)).exit_code == 0

    assert not (tmp_path / "config.yaml").exists()


def test_get_does_not_modify_an_existing_project_config(tmp_path: Path) -> None:
    project_config = tmp_path / "config.yaml"
    original = yaml.safe_dump({"site": {"image_format": "png"}})
    project_config.write_text(original)

    assert _get("-x", "site.image_format=webp", str(tmp_path)).exit_code == 0

    assert project_config.read_text() == original


def test_get_user_reads_the_user_config(isolated_environment: Path) -> None:
    isolated_environment.mkdir(parents=True)
    (isolated_environment / "config.yaml").write_text(
        yaml.safe_dump({"site": {"image_format": "png"}})
    )

    parsed = _parse(_get("--user"))

    assert parsed["site"]["image_format"] == "png"


def test_get_user_skips_the_project_layer(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """--user describes any project, so a config.yaml in the cwd is ignored."""
    (tmp_path / "config.yaml").write_text(
        yaml.safe_dump({"site": {"image_format": "png"}})
    )
    monkeypatch.chdir(tmp_path)

    parsed = _parse(_get("--user"))

    assert parsed["site"]["image_format"] == "jpg"


def test_get_needs_a_source_dir_or_user() -> None:
    assert _get().exit_code != 0


def test_get_rejects_user_with_a_source_dir(tmp_path: Path) -> None:
    assert _get("--user", str(tmp_path)).exit_code != 0


def test_get_rejects_a_missing_source_dir(tmp_path: Path) -> None:
    assert _get(str(tmp_path / "nope")).exit_code != 0


def test_write_rejects_a_missing_source_dir(tmp_path: Path) -> None:
    """Without the check this fails with a bare FileNotFoundError traceback."""
    result = CliRunner().invoke(
        config, ["-x", "site.image_format=webp", str(tmp_path / "nope")]
    )

    assert result.exit_code != 0
    assert not isinstance(result.exception, FileNotFoundError)
