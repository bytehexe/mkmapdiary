from pathlib import PosixPath

from mkmapdiary.lib.asset import AssetRecord
from mkmapdiary.lib.assetRegistry import AssetRegistry
from mkmapdiary.tasks.gpxTask import GPXTask
from mkmapdiary.tasks.siteTask import merge_creators


def test_track_creators_is_a_property() -> None:
    """Asserts on the class rather than an instance.

    GPXTask inherits BaseTask's abstract properties (config, db, dirs, cache,
    gettext, handle), so a bare instantiation raises TypeError before
    track_creators is ever reached -- not the AttributeError the brief
    expected. Per the brief's Step 2 fallback, assert on the class instead.
    """
    assert isinstance(GPXTask.track_creators, property)


def _registry(*creators: str | None) -> AssetRegistry:
    registry = AssetRegistry()
    for i, creator in enumerate(creators):
        registry.add_asset(
            AssetRecord(path=PosixPath(f"{i}.jpg"), type="image", creator=creator)
        )
    return registry


def test_distinct_creators_counts_none_as_a_value() -> None:
    assert _registry("Bob", None).distinct_creators() == {"Bob", None}


def test_distinct_creators_deduplicates() -> None:
    assert _registry("Bob", "Bob", "Bob").distinct_creators() == {"Bob"}


def test_empty_registry_has_no_creators() -> None:
    assert AssetRegistry().distinct_creators() == set()


def test_threshold_empty_journal() -> None:
    assert len(AssetRegistry().distinct_creators()) < 2


def test_threshold_uniform_single_creator_is_suppressed() -> None:
    assert len(_registry("Bob", "Bob").distinct_creators()) < 2


def test_threshold_all_unattributed_is_suppressed() -> None:
    assert len(_registry(None, None).distinct_creators()) < 2


def test_threshold_mixed_named_and_unattributed_is_shown() -> None:
    """Bob shot one directory and the rest is unattributed — a real distinction."""
    assert len(_registry("Bob", None).distinct_creators()) >= 2


def test_threshold_two_named_creators_is_shown() -> None:
    assert len(_registry("Bob", "Janna").distinct_creators()) >= 2


def test_merge_unions_all_three_sources() -> None:
    assert merge_creators(["Chris"], {"Bob"}, {"Alex"}) == ["Alex", "Bob", "Chris"]


def test_merge_deduplicates_across_sources() -> None:
    assert merge_creators(["Janna"], {"Janna", "Bob"}, {"Janna"}) == ["Bob", "Janna"]


def test_merge_drops_the_none_placeholder() -> None:
    """distinct_creators keeps None as a value; the credits page must not."""
    assert merge_creators([], {"Bob", None}, set()) == ["Bob"]


def test_merge_of_nothing_is_empty() -> None:
    assert merge_creators([], set(), set()) == []
