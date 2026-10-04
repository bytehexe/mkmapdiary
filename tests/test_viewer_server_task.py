import pathlib

from mkmapdiary.tasks.siteTask import (
    clean_viewer_server_layout,
    viewer_server_platform_files,
)


def test_platform_files_cover_all_three_platforms() -> None:
    files = viewer_server_platform_files()
    names = {f.launcher_name for f in files}
    assert names == {
        "Open on Linux.sh",
        "Open on Mac.command",
        "Open on Windows.bat",
    }


def test_platform_files_map_to_correct_binary_platform_keys() -> None:
    files = viewer_server_platform_files()
    by_launcher = {f.launcher_name: f.platform for f in files}
    assert by_launcher["Open on Linux.sh"] == "linux"
    assert by_launcher["Open on Mac.command"] == "macos"
    assert by_launcher["Open on Windows.bat"] == "windows"


def test_switching_to_enabled_removes_stray_top_level_files(
    tmp_path: pathlib.Path,
) -> None:
    (tmp_path / "index.html").write_text("stale")
    (tmp_path / "credits.html").write_text("stale")
    (tmp_path / "assets").mkdir()
    (tmp_path / "_site").mkdir()
    (tmp_path / "Open on Linux.sh").write_text("#!/bin/sh")

    clean_viewer_server_layout(tmp_path, enabled=True)

    assert not (tmp_path / "index.html").exists()
    assert not (tmp_path / "credits.html").exists()
    assert not (tmp_path / "assets").exists()
    assert (tmp_path / "_site").exists()  # the current mode's own output stays
    assert (tmp_path / "Open on Linux.sh").exists()  # a launcher name stays


def test_switching_to_disabled_removes_launchers_and_site(
    tmp_path: pathlib.Path,
) -> None:
    (tmp_path / "Open on Linux.sh").write_text("#!/bin/sh")
    (tmp_path / "Open on Mac.command").write_text("#!/bin/sh")
    (tmp_path / "Open on Windows.bat").write_text("@echo off")
    (tmp_path / "_site").mkdir()
    (tmp_path / "_site" / "index.html").write_text("stale")

    clean_viewer_server_layout(tmp_path, enabled=False)

    assert not (tmp_path / "Open on Linux.sh").exists()
    assert not (tmp_path / "Open on Mac.command").exists()
    assert not (tmp_path / "Open on Windows.bat").exists()
    assert not (tmp_path / "_site").exists()


def test_cleanup_is_a_noop_on_a_fresh_empty_directory(tmp_path: pathlib.Path) -> None:
    clean_viewer_server_layout(tmp_path, enabled=True)
    clean_viewer_server_layout(tmp_path, enabled=False)
    assert list(tmp_path.iterdir()) == []


def test_cleanup_never_touches_the_dist_dir_marker(tmp_path: pathlib.Path) -> None:
    marker = tmp_path / ".mkmapdiary_dist_dir"
    marker.touch()
    clean_viewer_server_layout(tmp_path, enabled=True)
    clean_viewer_server_layout(tmp_path, enabled=False)
    assert marker.is_file()
