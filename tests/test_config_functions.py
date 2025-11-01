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

    @patch("mkmapdiary.lib.config.auto_detect_timezone")
    def test_auto_constructor_timezone(self, mock_auto_detect_timezone: Mock) -> None:
        """Test auto constructor for timezone detection."""
        mock_auto_detect_timezone.return_value = "Europe/Berlin"

        loader = MagicMock()
        node = MagicMock()
        loader.construct_scalar.return_value = "site.timezone"

        result = auto_constructor(loader, node)
        assert result == "Europe/Berlin"
        mock_auto_detect_timezone.assert_called_once()

    @patch("mkmapdiary.lib.config.auto_detect_timezone")
    def test_auto_constructor_timezone_failure(
        self, mock_auto_detect_timezone: Mock
    ) -> None:
        """Test auto constructor when timezone detection fails."""
        mock_auto_detect_timezone.return_value = None

        loader = MagicMock()
        node = MagicMock()
        loader.construct_scalar.return_value = "site.timezone"

        with pytest.raises(ValueError, match="Could not auto-detect timezone"):
            auto_constructor(loader, node)

    @patch("mkmapdiary.lib.config.auto_detect_locale")
    def test_auto_constructor_locale(self, mock_auto_detect_locale: Mock) -> None:
        """Test auto constructor for locale detection."""
        mock_auto_detect_locale.return_value = "en_US.UTF-8"

        loader = MagicMock()
        node = MagicMock()
        loader.construct_scalar.return_value = "site.locale"

        result = auto_constructor(loader, node)
        assert result == "en_US.UTF-8"
        mock_auto_detect_locale.assert_called_once()

    @patch("mkmapdiary.lib.config.auto_detect_locale")
    def test_auto_constructor_locale_failure(
        self, mock_auto_detect_locale: Mock
    ) -> None:
        """Test auto constructor when locale detection fails."""
        mock_auto_detect_locale.return_value = None

        loader = MagicMock()
        node = MagicMock()
        loader.construct_scalar.return_value = "site.locale"

        with pytest.raises(ValueError, match="Could not auto-detect locale"):
            auto_constructor(loader, node)

    def test_auto_constructor_transcription_enabled(self) -> None:
        """Test auto constructor for transcription capability detection."""
        loader = MagicMock()
        node = MagicMock()
        loader.construct_scalar.return_value = "transcription.enabled"

        # Test case where whisper is available (mocked)
        with patch.dict("sys.modules", {"whisper": MagicMock()}):
            result = auto_constructor(loader, node)
            assert result is True

    def test_auto_constructor_transcription_disabled(self) -> None:
        """Test auto constructor when transcription is not available."""
        loader = MagicMock()
        node = MagicMock()
        loader.construct_scalar.return_value = "transcription.enabled"

        # Test case where whisper import fails
        with patch("builtins.__import__", side_effect=ImportError):
            result = auto_constructor(loader, node)
            assert result is False

    def test_auto_constructor_unknown_value(self) -> None:
        """Test auto constructor with unknown auto value."""
        loader = MagicMock()
        node = MagicMock()
        loader.construct_scalar.return_value = "unknown.value"

        with pytest.raises(ValueError, match="Unknown auto value: unknown.value"):
            auto_constructor(loader, node)


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
        timezone: !auto site.timezone
        """

        config = yaml.load(yaml_content, Loader=ConfigLoader)

        assert config["timezone"] == "America/New_York"

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
