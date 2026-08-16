from collections.abc import Callable
from pathlib import PosixPath
from typing import Any, cast

from mkmapdiary.lib.asset import AssetRecord
from mkmapdiary.lib.assetRegistry import AssetRegistry
from mkmapdiary.lib.calibration import Calibration
from mkmapdiary.lib.dirs import Dirs
from mkmapdiary.tasks.gpxTask import GPXTask
from mkmapdiary.tasks.siteTask import merge_creators


class _GPXTask(GPXTask):
    """GPXTask made instantiable by satisfying BaseTask's abstract members.

    handle_gpx touches none of them, so plain stubs suffice -- no config, no
    build directory, no filesystem.
    """

    config: dict = {}
    db = AssetRegistry()
    dirs = cast(Dirs, None)
    cache: dict = {}

    @property
    def gettext(self) -> Callable:
        return lambda message: message

    def handle(self, source: PosixPath) -> list[Any]:
        return []


def _handled(*creators: str | None) -> set[str]:
    """Feed one GPX source per creator through handle_gpx."""
    task = _GPXTask()
    for i, creator in enumerate(creators):
        task.handle_gpx(
            PosixPath(f"{i}.gpx"),
            Calibration(timezone="UTC", offset=0, creator=creator),
        )
    return task.track_creators


def test_track_creators_collects_the_source_creator() -> None:
    assert _handled("Bob") == {"Bob"}


def test_track_creators_deduplicates_across_sources() -> None:
    assert _handled("Bob", "Bob", "Janna") == {"Bob", "Janna"}


def test_track_creators_drops_unattributed_sources() -> None:
    """None is not a creator here -- the credits page has nothing to name."""
    assert _handled("Bob", None) == {"Bob"}


def test_track_creators_of_no_sources_is_empty() -> None:
    assert _handled() == set()


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


def _with_merged_track(registry: AssetRegistry) -> AssetRegistry:
    """Add the per-date GPX record GPXTask builds, which has no creator."""
    registry.add_asset(AssetRecord(path=PosixPath("2026-08-02.gpx"), type="gpx"))
    return registry


def test_merged_track_does_not_count_as_a_creator() -> None:
    """A track is stitched from many sources, so its None is not a value.

    Without this, every journal holding a GPX track would have a second
    distinct value and the uniform-creator case could never be suppressed.
    """
    registry = _with_merged_track(_registry("Bob", "Bob"))
    assert registry.distinct_creators() == {"Bob"}


def test_merged_track_does_not_force_creators_to_show() -> None:
    assert len(_with_merged_track(_registry("Bob", "Bob")).distinct_creators()) < 2


def test_merge_unions_all_three_sources() -> None:
    assert merge_creators(["Chris"], {"Bob"}, {"Alex"}) == ["Alex", "Bob", "Chris"]


def test_merge_deduplicates_across_sources() -> None:
    assert merge_creators(["Janna"], {"Janna", "Bob"}, {"Janna"}) == ["Bob", "Janna"]


def test_merge_drops_the_none_placeholder() -> None:
    """distinct_creators keeps None as a value; the credits page must not."""
    assert merge_creators([], {"Bob", None}, set()) == ["Bob"]


def test_merge_of_nothing_is_empty() -> None:
    assert merge_creators([], set(), set()) == []
