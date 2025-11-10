import importlib.util
import logging
import pathlib
import shutil
import sys
from collections.abc import MutableMapping, Sequence
from typing import Any

import humanfriendly
import jsonschema
import yaml
from jsonschema.exceptions import ValidationError

from mkmapdiary import util
from mkmapdiary.util.locale import auto_detect_locale, auto_detect_timezone

logger = logging.getLogger(__name__)


class AutoValue:
    """Placeholder class for auto-detected configuration values"""


def auto_constructor(loader: yaml.SafeLoader, node: yaml.ScalarNode) -> Any:
    """Constructor for !auto tag that returns an AutoValue object"""

    # Make sure the node has no value
    if not isinstance(node, yaml.ScalarNode) or node.value not in ("", None):
        raise ValueError("!auto tag does not accept a value")

    return AutoValue()


def calculate_auto_value(path: str) -> Any:
    if path == "site.timezone":
        tz = auto_detect_timezone()
        if tz is None:
            raise ValueError("Could not auto-detect timezone")
        return tz
    elif path == "site.locale":
        loc = auto_detect_locale()
        if loc is None:
            raise ValueError("Could not auto-detect locale")
        return loc
    elif path == "features.transcription.enabled":
        return importlib.util.find_spec("whisper") is not None
    elif path == "features.iqa.method":
        if (
            importlib.util.find_spec("torch") is not None
            and importlib.util.find_spec("torchvision") is not None
            and importlib.util.find_spec("piq") is not None
        ):
            return "clipiqa"
        else:
            return "simple"
    elif (
        path == "features.gpsbabel_import.enabled"
        or path == "features.track_simplification.enabled"
    ):
        return bool(shutil.which("gpsbabel"))
    else:
        raise ValueError(f"Unknown auto value: {path}")


def find_and_replace_auto_values(data: Any, base_path: str = "") -> Any:
    """Recursively find and replace AutoValue instances in the data structure."""
    if isinstance(data, dict):
        return {
            key: find_and_replace_auto_values(
                value, f"{base_path}.{key}" if base_path else key
            )
            for key, value in data.items()
        }
    elif isinstance(data, list):
        return [
            find_and_replace_auto_values(item, f"{base_path}[{index}]")
            for index, item in enumerate(data)
        ]
    elif isinstance(data, AutoValue):
        return calculate_auto_value(base_path)
    else:
        return data


def duration_constructor(loader: yaml.SafeLoader, node: yaml.ScalarNode) -> int:
    """Constructor for !duration tag that converts ISO 8601 duration strings to seconds"""
    value = loader.construct_scalar(node)
    if isinstance(value, (int, float)):
        return int(value)
    return int(humanfriendly.parse_timespan(value))


def distance_constructor(loader: yaml.SafeLoader, node: yaml.ScalarNode) -> float:
    """Constructor for !distance tag that converts distance strings to meters"""
    value = loader.construct_scalar(node)
    if isinstance(value, (int, float)):
        return float(value)
    return float(humanfriendly.parse_length(value))


class ConfigLoader(yaml.SafeLoader):
    """Custom YAML loader with !auto tag support"""


# Register the custom constructor only for our custom loader
ConfigLoader.add_constructor("!auto", auto_constructor)
ConfigLoader.add_constructor("!duration", duration_constructor)
ConfigLoader.add_constructor("!distance", distance_constructor)


def load_config_file(path: pathlib.Path) -> dict[str, Any]:
    with open(path) as file:
        config = yaml.load(file, Loader=ConfigLoader)

    return load_config_data(config)


def load_config_data(config: dict[str, Any]) -> dict[str, Any]:
    with open(
        pathlib.Path(__file__).parent.parent / "resources" / "config_schema.yaml",
    ) as defaults_file:
        schema = yaml.load(defaults_file, Loader=ConfigLoader)

    config = find_and_replace_auto_values(config)
    jsonschema.validate(instance=config, schema=schema)

    return config


def load_config_param(param: str) -> dict:
    config_data: dict[str, Any] = {}

    key, value = param.split("=", 1)
    key_list = key.split(".")
    d = config_data
    for k in key_list[:-1]:
        d = d.setdefault(k, {})
    d[key_list[-1]] = yaml.load(value, Loader=ConfigLoader)

    return load_config_data(config_data)


def write_config(source_dir: pathlib.Path, params: Sequence[str]) -> None:
    """Write configuration data to a YAML file at the specified path."""

    config_path = source_dir / "config.yaml"
    if config_path.is_file():
        config_data: MutableMapping[str, Any] = load_config_file(config_path)
    else:
        config_data = {}

    for param in params:
        try:
            param_config = load_config_param(param)
            config_data = util.deep_update(config_data, param_config)
        except ValidationError as e:
            logger.error(f"Config parameter '{param}' is invalid: {e.message}")
            logger.info(f"Path: {'.'.join(str(p) for p in e.path)}")
            sys.exit(1)
        except ValueError as e:
            logger.error(f"Error loading config parameter '{param}': {e}")
            sys.exit(1)

    if params:
        load_config_data(dict(config_data))  # Validate final config

        with open(config_path, "w") as file:
            yaml.dump(config_data, file, sort_keys=False)
        logger.info(f"Wrote configuration to {config_path}")
    else:
        logger.info(
            f"No parameters provided; configuration file {config_path} not modified.",
        )

    if config_path.is_file():
        with open(config_path) as file:
            logger.debug(
                "Configuration file contents:\n%s",
                file.read(),
                extra={"icon": "📄"},
            )
