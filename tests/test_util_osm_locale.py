import pytest

from mkmapdiary.util.locale import get_language
from mkmapdiary.util.osm import calculate_rank, clip_rank


class TestCalculateRank:
    """Test the calculate_rank function (expanding existing tests)."""

    def test_calculate_rank_by_radius(self):
        """Test rank calculation based on radius."""
        # Test cases from existing test_rank.py
        assert calculate_rank(radius=1000) == 20
        assert calculate_rank(radius=2000) == 19
        assert calculate_rank(radius=4000) == 18
        assert calculate_rank(radius=8000) == 17
        assert calculate_rank(radius=8002) == 17

        # Additional edge cases
        assert calculate_rank(radius=500) == 21
        assert calculate_rank(radius=250) == 22
        assert calculate_rank(radius=125) == 23

        # Large radius should return None
        assert calculate_rank(radius=60000) in (13, 14, 15, 16)

    def test_calculate_rank_by_place(self):
        """Test rank calculation based on place type."""
        # Test cases from existing test_rank.py
        assert calculate_rank(place="city") == 13
        assert calculate_rank(place="town") == 17
        assert calculate_rank(place="village") == 19
        assert calculate_rank(place="hamlet") == 20
        assert calculate_rank(place="isolated_dwelling") == 21

        # Additional place types
        assert calculate_rank(place="municipality") == 13
        assert calculate_rank(place="island") == 13
        assert calculate_rank(place="borough") == 17
        assert calculate_rank(place="suburb") == 19
        assert calculate_rank(place="quarter") == 19
        assert calculate_rank(place="farm") == 20
        assert calculate_rank(place="neighbourhood") == 20
        assert calculate_rank(place="islet") == 20
        assert calculate_rank(place="single_dwelling") == 21
        assert calculate_rank(place="city_block") == 21
        assert calculate_rank(place="locality") == 21
        assert calculate_rank(place="croft") == 23
        assert calculate_rank(place="allotments") == 23
        assert calculate_rank(place="garden") == 23
        assert calculate_rank(place="plot") == 23
        assert calculate_rank(place="square") == 23
        assert calculate_rank(place="festival") == 23

    def test_calculate_rank_defaults_and_unknowns(self):
        """Test default behavior and unknown place types."""
        # No arguments should return default rank
        assert calculate_rank() == 23

        # Unknown place types should return None
        assert calculate_rank(place="unknown_place") is None
        assert calculate_rank(place="nonexistent") is None
        assert calculate_rank(place="") is None

    def test_calculate_rank_precedence(self):
        """Test that radius takes precedence over place when both are provided."""
        # Radius should be used when both radius and place are provided
        assert (
            calculate_rank(radius=1000, place="city") == 20
        )  # radius result, not city (13)


class TestClipRank:
    """Test the clip_rank function."""

    def test_clip_rank_within_bounds(self):
        """Test clipping ranks within valid bounds."""
        assert clip_rank(15) == 15
        assert clip_rank(13) == 13  # MIN_RANK
        assert clip_rank(23) == 23  # MAX_RANK

    def test_clip_rank_below_minimum(self):
        """Test clipping ranks below minimum."""
        assert clip_rank(10) == 13
        assert clip_rank(0) == 13
        assert clip_rank(-5) == 13

    def test_clip_rank_above_maximum(self):
        """Test clipping ranks above maximum."""
        assert clip_rank(25) == 23
        assert clip_rank(30) == 23
        assert clip_rank(100) == 23


class TestGetLanguage:
    """Test the get_language function."""

    def test_get_language_standard_locales(self):
        """Test language extraction from standard locale strings."""
        assert get_language("en_US") == "en"
        assert get_language("de_DE") == "de"
        assert get_language("fr_FR") == "fr"
        assert get_language("es_ES") == "es"
        assert get_language("ja_JP") == "ja"
        assert get_language("zh_CN") == "zh"

    def test_get_language_with_encoding(self):
        """Test language extraction from locales with encoding."""
        assert get_language("en_US.UTF-8") == "en"
        assert get_language("de_DE.UTF-8") == "de"
        assert get_language("fr_CA.ISO-8859-1") == "fr"

    def test_get_language_variants(self):
        """Test language extraction from locale variants."""
        assert get_language("en_GB") == "en"
        assert get_language("en_CA") == "en"
        assert get_language("de_AT") == "de"
        assert get_language("de_CH") == "de"
        assert get_language("pt_BR") == "pt"
        assert get_language("zh_TW") == "zh"

    def test_get_language_language_only(self):
        """Test language extraction when only language code is provided."""
        assert get_language("en") == "en"
        assert get_language("de") == "de"
        assert get_language("fr") == "fr"

    def test_get_language_edge_cases(self):
        """Test edge cases for get_language."""
        # Empty string
        assert get_language("") == ""

        # Complex locale strings
        assert get_language("en_US.UTF-8@variant") == "en"
        assert get_language("de_DE_phonebook") == "de"
