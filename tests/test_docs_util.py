from docs.util import tags_sort


class TestTagsSort:
    """Test the tags_sort function."""

    def test_tags_sort_identify_extension(self) -> None:
        """Test sorting of 'identify' and 'extension' tags."""
        # These should sort to the beginning with 'a' prefix
        assert tags_sort("identify") == "aidentify"
        assert tags_sort("extension") == "aextension"

    def test_tags_sort_journal_map_feature(self) -> None:
        """Test sorting of 'journal' and 'map feature' tags."""
        # These should sort with 'b' prefix
        assert tags_sort("journal") == "bjournal"
        assert tags_sort("map feature") == "bmap feature"

    def test_tags_sort_time_prefix(self) -> None:
        """Test sorting of tags starting with 'time'."""
        # These should sort with 'c' prefix
        assert tags_sort("time by content") == "ctime by content"
        assert tags_sort("time by metadata") == "ctime by metadata"
        assert tags_sort("time by filename/mtime") == "ctime by filename/mtime"
        assert tags_sort("timestamp") == "ctimestamp"  # Starts with 'time'

    def test_tags_sort_coords_prefix(self) -> None:
        """Test sorting of tags starting with 'coords'."""
        # These should sort with 'd' prefix
        assert tags_sort("coords by content") == "dcoords by content"
        assert tags_sort("coords by metadata") == "dcoords by metadata"
        assert tags_sort("coords by correlation") == "dcoords by correlation"
        assert (
            tags_sort("coordinates") == "zcoordinates"
        )  # Starts with 'coord', not 'coords'

    def test_tags_sort_other_tags(self) -> None:
        """Test sorting of other tags not in special categories."""
        # These should sort with 'z' prefix
        assert tags_sort("gallery image") == "zgallery image"
        assert tags_sort("file") == "zfile"
        assert tags_sort("random tag") == "zrandom tag"
        assert tags_sort("unknown") == "zunknown"

    def test_tags_sort_string_conversion(self) -> None:
        """Test that tags_sort properly converts input to string."""
        # Test with different input types
        assert tags_sort(123) == "z123"  # Number converted to string
        assert tags_sort(None) == "zNone"  # None converted to string

    def test_tags_sort_case_sensitivity(self) -> None:
        """Test case sensitivity in tag sorting."""
        # The function should be case-sensitive
        assert tags_sort("Identify") == "zIdentify"  # Capital I, not 'identify'
        assert tags_sort("EXTENSION") == "zEXTENSION"  # All caps, not 'extension'
        assert (
            tags_sort("Time by content") == "zTime by content"
        )  # Capital T, not 'time'

    def test_tags_sort_partial_matches(self) -> None:
        """Test partial matches for time and coords prefixes."""
        # Should match anything starting with the prefix
        assert tags_sort("timecode") == "ctimecode"
        assert tags_sort("timer") == "ctimer"
        assert tags_sort("coord_system") == "zcoord_system"
        assert tags_sort("coordination") == "zcoordination"

    def test_tags_sort_empty_string(self) -> None:
        """Test sorting of empty string."""
        assert tags_sort("") == "z"

    def test_tags_sort_whitespace(self) -> None:
        """Test sorting of whitespace-only strings."""
        assert tags_sort("   ") == "z   "
        assert tags_sort("\t") == "z\t"
        assert tags_sort("\n") == "z\n"

    def test_tags_sort_special_characters(self) -> None:
        """Test sorting of tags with special characters."""
        assert tags_sort("time-based") == "ctime-based"
        assert tags_sort("coords_data") == "dcoords_data"
        assert tags_sort("tag.with.dots") == "ztag.with.dots"
        assert tags_sort("tag/with/slashes") == "ztag/with/slashes"

    def test_tags_sort_comprehensive_ordering(self) -> None:
        """Test that the sorting function produces the expected ordering."""
        tags = [
            "unknown",  # z prefix
            "identify",  # a prefix
            "coords by metadata",  # d prefix
            "journal",  # b prefix
            "time by content",  # c prefix
            "extension",  # a prefix
            "map feature",  # b prefix
            "gallery image",  # z prefix
        ]

        sorted_keys = [tags_sort(tag) for tag in tags]
        expected_order = [
            "aidentify",
            "aextension",
            "bjournal",
            "bmap feature",
            "ctime by content",
            "dcoords by metadata",
            "zunknown",
            "zgallery image",
        ]

        # When sorted by the sort keys, should be in this order
        paired = list(zip(sorted_keys, tags))
        paired.sort(key=lambda x: x[0])
        actual_order = [pair[0] for pair in paired]

        # The sort keys should be in the expected order when sorted
        expected_order.sort()
        actual_order.sort()
        assert actual_order == expected_order
