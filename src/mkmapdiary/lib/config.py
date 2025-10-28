import pathlib
from typing import Any, Dict

import humanfriendly
import jsonschema
import yaml
from jsonschema import Draft202012Validator, validators

from mkmapdiary.util.locale import auto_detect_locale, auto_detect_timezone


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
