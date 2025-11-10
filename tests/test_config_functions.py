from unittest.mock import MagicMock, Mock, patch

import pytest
import yaml

from mkmapdiary.lib.config import ConfigLoader, auto_constructor, duration_constructor


class TestDurationConstructor:
    """Test the duration_constructor function."""

    def test_duration_constructor_integer(self) -> None:
        """Test duration constructor with integer values."""
        loader = MagicMock()
        node = MagicMock()
        loader.construct_scalar.return_value = 300

        result = duration_constructor(loader, node)
        assert result == 300

    def test_duration_constructor_float(self) -> None:
        """Test duration constructor with float values."""
        loader = MagicMock()
        node = MagicMock()
        loader.construct_scalar.return_value = 300.5

        result = duration_constructor(loader, node)
        assert result == 300  # Should be converted to int

    def test_duration_constructor_humanfriendly_formats(self) -> None:
        """Test duration constructor with human-friendly time formats."""
        test_cases = [
            ("5 minutes", 300),  # 5 * 60 = 300
            ("2 hours", 7200),  # 2 * 60 * 60 = 7200
            ("1 day", 86400),  # 24 * 60 * 60 = 86400
            ("30 seconds", 30),
            ("1.5 hours", 5400),  # 1.5 * 60 * 60 = 5400
        ]

        for time_str, expected_seconds in test_cases:
            loader = MagicMock()
            node = MagicMock()
            loader.construct_scalar.return_value = time_str

            result = duration_constructor(loader, node)
            assert result == expected_seconds

    def test_duration_constructor_zero(self) -> None:
        """Test duration constructor with zero values."""
        loader = MagicMock()
        node = MagicMock()
        loader.construct_scalar.return_value = "0 seconds"

        result = duration_constructor(loader, node)
        assert result == 0


class TestAutoConstructor:
    """Test the auto_constructor function."""

    def test_auto_constructor_empty_value(self) -> None:
        """Test auto constructor with empty value."""
        loader = MagicMock()
        node = yaml.ScalarNode(tag="!auto", value="")

        result = auto_constructor(loader, node)
        from mkmapdiary.lib.config import AutoValue

        assert isinstance(result, AutoValue)

    def test_auto_constructor_none_value(self) -> None:
        """Test auto constructor with None value."""
        loader = MagicMock()
        node = yaml.ScalarNode(tag="!auto", value=None)

        result = auto_constructor(loader, node)
        from mkmapdiary.lib.config import AutoValue

        assert isinstance(result, AutoValue)

    def test_auto_constructor_with_value_raises_error(self) -> None:
        """Test auto constructor raises error when value is provided."""
        loader = MagicMock()
        node = yaml.ScalarNode(tag="!auto", value="site.timezone")

        with pytest.raises(ValueError, match="!auto tag does not accept a value"):
            auto_constructor(loader, node)


class TestCalculateAutoValue:
    """Test the calculate_auto_value function."""

    @patch("mkmapdiary.lib.config.auto_detect_timezone")
    def test_calculate_auto_value_timezone(
        self, mock_auto_detect_timezone: Mock
    ) -> None:
        """Test calculate_auto_value for timezone detection."""
        from mkmapdiary.lib.config import calculate_auto_value

        mock_auto_detect_timezone.return_value = "Europe/Berlin"

        result = calculate_auto_value("site.timezone")
        assert result == "Europe/Berlin"
        mock_auto_detect_timezone.assert_called_once()

    @patch("mkmapdiary.lib.config.auto_detect_timezone")
    def test_calculate_auto_value_timezone_failure(
        self, mock_auto_detect_timezone: Mock
    ) -> None:
        """Test calculate_auto_value when timezone detection fails."""
        from mkmapdiary.lib.config import calculate_auto_value

        mock_auto_detect_timezone.return_value = None

        with pytest.raises(ValueError, match="Could not auto-detect timezone"):
            calculate_auto_value("site.timezone")

    @patch("mkmapdiary.lib.config.auto_detect_locale")
    def test_calculate_auto_value_locale(self, mock_auto_detect_locale: Mock) -> None:
        """Test calculate_auto_value for locale detection."""
        from mkmapdiary.lib.config import calculate_auto_value

        mock_auto_detect_locale.return_value = "en_US.UTF-8"

        result = calculate_auto_value("site.locale")
        assert result == "en_US.UTF-8"
        mock_auto_detect_locale.assert_called_once()

    @patch("mkmapdiary.lib.config.auto_detect_locale")
    def test_calculate_auto_value_locale_failure(
        self, mock_auto_detect_locale: Mock
    ) -> None:
        """Test calculate_auto_value when locale detection fails."""
        from mkmapdiary.lib.config import calculate_auto_value

        mock_auto_detect_locale.return_value = None

        with pytest.raises(ValueError, match="Could not auto-detect locale"):
            calculate_auto_value("site.locale")

    @patch("mkmapdiary.lib.config.importlib.util.find_spec")
    def test_calculate_auto_value_transcription_enabled(
        self, mock_find_spec: Mock
    ) -> None:
        """Test calculate_auto_value for transcription capability detection."""
        from mkmapdiary.lib.config import calculate_auto_value

        mock_find_spec.return_value = (
            MagicMock()
        )  # Non-None return means module is available

        result = calculate_auto_value("features.transcription.enabled")
        assert result is True
        mock_find_spec.assert_called_once_with("whisper")

    @patch("mkmapdiary.lib.config.importlib.util.find_spec")
    def test_calculate_auto_value_transcription_disabled(
        self, mock_find_spec: Mock
    ) -> None:
        """Test calculate_auto_value when transcription is not available."""
        from mkmapdiary.lib.config import calculate_auto_value

        mock_find_spec.return_value = None  # None return means module is not available

        result = calculate_auto_value("features.transcription.enabled")
        assert result is False
        mock_find_spec.assert_called_once_with("whisper")

    def test_calculate_auto_value_unknown_value(self) -> None:
        """Test calculate_auto_value with unknown auto value."""
        from mkmapdiary.lib.config import calculate_auto_value

        with pytest.raises(ValueError, match="Unknown auto value: unknown.value"):
            calculate_auto_value("unknown.value")


class TestFindAndReplaceAutoValues:
    """Test the find_and_replace_auto_values function."""

    @patch("mkmapdiary.lib.config.calculate_auto_value")
    def test_find_and_replace_dict(self, mock_calculate: Mock) -> None:
        """Test find_and_replace_auto_values with dictionary."""
        from mkmapdiary.lib.config import AutoValue, find_and_replace_auto_values

        mock_calculate.return_value = "Europe/Berlin"

        data = {"site": {"timezone": AutoValue(), "name": "My Site"}}

        result = find_and_replace_auto_values(data)
        assert result["site"]["timezone"] == "Europe/Berlin"
        assert result["site"]["name"] == "My Site"
        mock_calculate.assert_called_once_with("site.timezone")

    @patch("mkmapdiary.lib.config.calculate_auto_value")
    def test_find_and_replace_list(self, mock_calculate: Mock) -> None:
        """Test find_and_replace_auto_values with list."""
        from mkmapdiary.lib.config import AutoValue, find_and_replace_auto_values

        mock_calculate.return_value = "auto_value"

        data = ["normal", AutoValue(), "other"]

        result = find_and_replace_auto_values(data, "test_path")
        assert result[0] == "normal"
        assert result[1] == "auto_value"
        assert result[2] == "other"
        mock_calculate.assert_called_once_with("test_path[1]")

    def test_find_and_replace_no_auto_values(self) -> None:
        """Test find_and_replace_auto_values with no AutoValue objects."""
        from mkmapdiary.lib.config import find_and_replace_auto_values

        data = {"normal": "value", "number": 42, "list": ["a", "b", "c"]}

        result = find_and_replace_auto_values(data)
        assert result == data


class TestConfigLoaderIntegration:
    """Test the ConfigLoader class with custom constructors."""

    def test_config_loader_duration_tag(self) -> None:
        """Test that ConfigLoader properly handles !duration tags."""
        yaml_content = """
        timeout: !duration 5 minutes
        short_timeout: !duration 30 seconds
        """

        config = yaml.load(yaml_content, Loader=ConfigLoader)

        assert config["timeout"] == 300  # 5 minutes = 300 seconds
        assert config["short_timeout"] == 30

    @patch("mkmapdiary.lib.config.auto_detect_timezone")
    def test_config_loader_auto_tag(self, mock_auto_detect_timezone: Mock) -> None:
        """Test that ConfigLoader properly handles !auto tags."""
        mock_auto_detect_timezone.return_value = "America/New_York"

        yaml_content = """
        site:
          timezone: !auto
        """

        config = yaml.load(yaml_content, Loader=ConfigLoader)
        from mkmapdiary.lib.config import find_and_replace_auto_values

        # Need to process auto values after loading
        processed_config = find_and_replace_auto_values(config)

        assert processed_config["site"]["timezone"] == "America/New_York"

    def test_config_loader_auto_tag_creates_auto_value(self) -> None:
        """Test that !auto tag creates AutoValue object."""
        yaml_content = """
        site:
          timezone: !auto
        """

        config = yaml.load(yaml_content, Loader=ConfigLoader)

        from mkmapdiary.lib.config import AutoValue

        assert isinstance(config["site"]["timezone"], AutoValue)

    def test_config_loader_mixed_tags(self) -> None:
        """Test ConfigLoader with multiple custom tags."""
        yaml_content = """
        settings:
          timeout: !duration 2 hours
          cache_duration: !duration 1 day
        normal_value: "regular string"
        number: 42
        """

        config = yaml.load(yaml_content, Loader=ConfigLoader)

        assert config["settings"]["timeout"] == 7200  # 2 hours
        assert config["settings"]["cache_duration"] == 86400  # 1 day
        assert config["normal_value"] == "regular string"
        assert config["number"] == 42
