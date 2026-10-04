import pathlib

from mkmapdiary.lib.aiUsage import (
    TAGS,
    TITLE,
    TRANSCRIPT,
    record_usage,
    usage_path,
    used_keys,
)


def test_records_used_keys_for_a_scope(tmp_path: pathlib.Path) -> None:
    record_usage(tmp_path, "2026-04-09", [TAGS])

    assert used_keys(tmp_path, {"2026-04-09"}) == {TAGS}


def test_records_an_empty_marker_when_nothing_was_generated(
    tmp_path: pathlib.Path,
) -> None:
    """The marker is a doit target, so it must exist even with no usage.

    A missing target makes doit consider the task out of date, which would
    re-invoke the model on every build of an unchanged source.
    """
    record_usage(tmp_path, "2026-04-09", [])

    assert usage_path(tmp_path, "2026-04-09").is_file()
    assert used_keys(tmp_path, {"2026-04-09"}) == set()


def test_recording_again_replaces_the_previous_keys(tmp_path: pathlib.Path) -> None:
    record_usage(tmp_path, "2026-04-09", [TAGS])
    record_usage(tmp_path, "2026-04-09", [])

    assert used_keys(tmp_path, {"2026-04-09"}) == set()


def test_used_keys_unions_every_live_scope(tmp_path: pathlib.Path) -> None:
    record_usage(tmp_path, "2026-04-09", [TAGS])
    record_usage(tmp_path, "/build/docs/assets/note.md", [TITLE])
    record_usage(tmp_path, "/build/docs/assets/memo.mp3.md", [TITLE, TRANSCRIPT])

    assert used_keys(
        tmp_path,
        {
            "2026-04-09",
            "/build/docs/assets/note.md",
            "/build/docs/assets/memo.mp3.md",
        },
    ) == {TAGS, TITLE, TRANSCRIPT}


def test_used_keys_drops_scopes_that_are_no_longer_live(
    tmp_path: pathlib.Path,
) -> None:
    """Deleting a source from a persistent build dir leaves its marker behind.

    doit neither re-runs the vanished task nor removes its targets, so the
    reader prunes against the assets that still exist.
    """
    record_usage(tmp_path, "/build/docs/assets/note.md", [TITLE])
    record_usage(tmp_path, "/build/docs/assets/deleted.md", [TITLE])

    assert used_keys(tmp_path, {"/build/docs/assets/note.md"}) == {TITLE}
    assert used_keys(tmp_path, set()) == set()


def test_used_keys_is_empty_when_nothing_was_ever_recorded(
    tmp_path: pathlib.Path,
) -> None:
    assert used_keys(tmp_path / "absent", {"2026-04-09"}) == set()


def test_records_survive_a_run_that_regenerates_nothing(
    tmp_path: pathlib.Path,
) -> None:
    """The disclosure must hold up across an incremental `-B` build.

    doit skips the tags/text/audio tasks when their sources are unchanged, so
    no model runs on the second build — but the credits page rebuilds
    unconditionally. Reading live state instead of these records would drop
    every row from a journal that still contains the generated content.
    """
    scopes = {"2026-04-09", "/build/docs/assets/memo.mp3.md"}

    # First build: the tasks run and record what they generated.
    record_usage(tmp_path, "2026-04-09", [TAGS])
    record_usage(tmp_path, "/build/docs/assets/memo.mp3.md", [TITLE, TRANSCRIPT])

    # Second build: every generating task is up to date, so none of them runs.
    assert used_keys(tmp_path, scopes) == {TAGS, TITLE, TRANSCRIPT}


def test_usage_path_is_stable_and_scope_specific(tmp_path: pathlib.Path) -> None:
    """Tasks declare the path as a target before the action computes it."""
    assert usage_path(tmp_path, "2026-04-09") == usage_path(tmp_path, "2026-04-09")
    assert usage_path(tmp_path, "2026-04-09") != usage_path(tmp_path, "2026-04-10")
