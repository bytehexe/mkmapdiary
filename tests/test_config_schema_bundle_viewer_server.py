from pathlib import Path

import pytest
from jsonschema.exceptions import ValidationError

from mkmapdiary.lib.config import load_config_data, load_config_file

RESOURCES = Path(__file__).parent.parent / "src" / "mkmapdiary" / "resources"


def test_defaults_declare_bundle_viewer_server_enabled_true() -> None:
    config = load_config_file(RESOURCES / "defaults.yaml")
    assert config["features"]["bundle_viewer_server"]["enabled"] is True


def test_defaults_validate_against_schema() -> None:
    # Verify that the entire defaults.yaml file validates against the schema.
    # load_config_file internally validates against the schema and raises
    # ValidationError if it fails, so successful load proves validation passed.
    config = load_config_file(RESOURCES / "defaults.yaml")
    # Verify the entire config structure is present by checking expected top-level keys
    assert "features" in config
    assert "site" in config
    assert "credits" in config
    assert "strings" in config
    assert "input_formats" in config


def test_schema_rejects_unknown_bundle_viewer_server_key() -> None:
    instance = {"features": {"bundle_viewer_server": {"enabled": True, "bogus": 1}}}

    with pytest.raises(ValidationError):
        load_config_data(instance)
