from mkmapdiary.tasks.base.exifReader import ExifData, artist_from_exif


def test_reads_the_exif_artist_tag() -> None:
    assert artist_from_exif({"EXIF:Artist": "Bob Ross"}) == "Bob Ross"


def test_falls_back_to_iptc_byline() -> None:
    assert artist_from_exif({"IPTC:By-line": "Bob Ross"}) == "Bob Ross"


def test_falls_back_to_xmp_creator() -> None:
    assert artist_from_exif({"XMP:Creator": "Bob Ross"}) == "Bob Ross"


def test_exif_artist_wins_over_the_others() -> None:
    exif = {
        "EXIF:Artist": "Bob",
        "IPTC:By-line": "Janna",
        "XMP:Creator": "Alex",
    }
    assert artist_from_exif(exif) == "Bob"


def test_absent_tags_give_none() -> None:
    assert artist_from_exif({}) is None
    assert artist_from_exif({"EXIF:Make": "Canon"}) is None


def test_blank_tags_count_as_absent() -> None:
    """Cameras write an empty Artist field when the setting was never used."""
    assert artist_from_exif({"EXIF:Artist": ""}) is None
    assert artist_from_exif({"EXIF:Artist": "   "}) is None


def test_a_blank_tag_does_not_block_a_later_one() -> None:
    assert artist_from_exif({"EXIF:Artist": "  ", "IPTC:By-line": "Janna"}) == "Janna"


def test_values_are_stripped() -> None:
    assert artist_from_exif({"EXIF:Artist": "  Bob Ross \n"}) == "Bob Ross"


def test_non_string_values_are_ignored() -> None:
    """exiftool returns numbers for some tags; never crash on one."""
    assert artist_from_exif({"EXIF:Artist": 0}) is None


def test_exifdata_defaults_artist_to_none() -> None:
    assert ExifData().artist is None
