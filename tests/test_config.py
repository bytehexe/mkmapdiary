import jsonschema.exceptions
import pytest

from mkmapdiary.lib import config


def test_config_validation():
    """Test that the configuration validation works correctly."""

    # Valid configuration
    valid_config = {
        "features": {
            "geo_correlation": {
                "time_offset": 0,
            },
        },
        "site": {
            "locale": "de_DE.UTF-8",
        },
    }

    # This should not raise any exceptions
    config.load_config_data(valid_config)

    # Invalid configuration: wrong type for time_offset
    invalid_config = {
        "features": {
            "geo_correlation": {
                "time_offset": "123",  # Should be int
            },
        }
    }

    with pytest.raises(jsonschema.exceptions.ValidationError):
        config.load_config_data(invalid_config)


def test_config_param_loading():
    """Test loading configuration from a parameter string."""

    param = "site.timezone=UTC"
    loaded_config = config.load_config_param(param)

    assert loaded_config["site"]["timezone"] == "UTC"

    param_duration = "features.geo_correlation.time_offset=!duration 5 minutes"
    loaded_config_duration = config.load_config_param(param_duration)

    assert loaded_config_duration["features"]["geo_correlation"]["time_offset"] == 300
    param_duration_int = "features.geo_correlation.time_offset=!duration 600"
    loaded_config_duration_int = config.load_config_param(param_duration_int)

    assert (
        loaded_config_duration_int["features"]["geo_correlation"]["time_offset"] == 600
    )  # 600 seconds
