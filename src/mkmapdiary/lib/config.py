import logging
import pathlib
import sys
from typing import Any, Dict

import humanfriendly
import jsonschema
import yaml
from jsonschema import Draft202012Validator, validators
from jsonschema.exceptions import ValidationError

from mkmapdiary import util
from mkmapdiary.util.locale import auto_detect_locale, auto_detect_timezone

logger = logging.getLogger(__name__)


def auto_constructor(loader, node) -> Any:
    """Constructor for !auto tag that returns an AutoValue object"""
    value = loader.construct_scalar(node)
    if value == "site.timezone":
        tz = auto_detect_timezone()
        if tz is None:
            raise ValueError("Could not auto-detect timezone")
        return tz
    elif value == "site.locale":
        loc = auto_detect_locale()
        if loc is None:
            raise ValueError("Could not auto-detect locale")
        return loc
    elif value == "transcription.enabled":
        try:
            import whisper  # noqa: F401

            return True
        except ImportError:
            return False
    else:
        raise ValueError(f"Unknown auto value: {value}")


def duration_constructor(loader, node):
    """Constructor for !duration tag that converts ISO 8601 duration strings to seconds"""
    value = loader.construct_scalar(node)
    if isinstance(value, (int, float)):
        return int(value)
    return int(humanfriendly.parse_timespan(value))


class ConfigLoader(yaml.SafeLoader):
    """Custom YAML loader with !auto tag support"""


# Register the custom constructor only for our custom loader
ConfigLoader.add_constructor("!auto", auto_constructor)
ConfigLoader.add_constructor("!duration", duration_constructor)


def load_config_file(path: pathlib.Path) -> dict:
    with open(path, "r") as file:
        config = yaml.load(file, Loader=ConfigLoader)

    return load_config_data(config)


def load_config_data(config: dict) -> dict:
    with open(
        pathlib.Path(__file__).parent.parent / "resources" / "config_schema.yaml", "r"
    ) as defaults_file:
        schema = yaml.load(defaults_file, Loader=ConfigLoader)

    jsonschema.validate(instance=config, schema=schema)

    return config


def load_config_param(param: str) -> dict:
    config_data: Dict[str, Any] = {}

    key, value = param.split("=", 1)
    key_list = key.split(".")
    d = config_data
    for k in key_list[:-1]:
        d = d.setdefault(k, {})
    d[key_list[-1]] = yaml.load(value, Loader=ConfigLoader)

    return load_config_data(config_data)


def write_config(source_dir: pathlib.Path, params: list) -> None:
    """Write configuration data to a YAML file at the specified path."""

    config_path = source_dir / "config.yaml"
    if config_path.is_file():
        config_data = load_config_file(config_path)
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
        load_config_data(config_data)  # Validate final config

        with open(config_path, "w") as file:
            yaml.dump(config_data, file, sort_keys=False)
        logger.info(f"Wrote configuration to {config_path}")
    else:
        logger.info(
            f"No parameters provided; configuration file {config_path} not modified."
        )

    if config_path.is_file():
        with open(config_path, "r") as file:
            logger.debug(
                "Configuration file contents:\n%s", file.read(), extra={"icon": "📄"}
            )
