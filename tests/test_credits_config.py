from pathlib import Path
from typing import Any

import pytest
from jsonschema.exceptions import ValidationError

from mkmapdiary.lib.config import load_config_data, load_config_file

RESOURCES = Path(__file__).parent.parent / "src" / "mkmapdiary" / "resources"

CREDITS_STRINGS = (
    "credits_title",
    "credits_travellers",
    "credits_made_with",
    "credits_software",
    "credits_toolchain",
)


def test_defaults_have_empty_travellers() -> None:
    config = load_config_file(RESOURCES / "defaults.yaml")

    assert config["credits"]["travellers"] == []


def test_defaults_declare_credits_strings() -> None:
    config = load_config_file(RESOURCES / "defaults.yaml")

    for key in CREDITS_STRINGS:
        assert key in config["strings"], key
        assert config["strings"][key] is None


def test_travellers_accepts_a_list_of_names() -> None:
    config: dict[str, Any] = {"credits": {"travellers": ["Janna Hopp", "Alex"]}}

    assert load_config_data(config)["credits"]["travellers"] == ["Janna Hopp", "Alex"]


def test_travellers_rejects_a_bare_string() -> None:
    with pytest.raises(ValidationError):
        load_config_data({"credits": {"travellers": "Janna Hopp"}})


def test_travellers_rejects_non_string_entries() -> None:
    with pytest.raises(ValidationError):
        load_config_data({"credits": {"travellers": [42]}})
