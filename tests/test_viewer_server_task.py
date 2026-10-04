import pathlib

from mkmapdiary.tasks.siteTask import (
    clean_viewer_server_layout,
    copy_viewer_server_license,
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
    by_launcher = {f.launcher_name: f.binaries for f in files}
    assert by_launcher["Open on Linux.sh"] == (("linux", "miniserve-linux"),)
    assert by_launcher["Open on Mac.command"] == (
        ("macos-x86_64", "miniserve-macos-x86_64"),
        ("macos-arm64", "miniserve-macos-arm64"),
    )
    assert by_launcher["Open on Windows.bat"] == (("windows", "miniserve-windows.exe"),)


def test_four_binaries_total_across_all_platform_files() -> None:
    files = viewer_server_platform_files()
    all_platform_keys = {platform_key for f in files for platform_key, _ in f.binaries}
    assert all_platform_keys == {
        "linux",
        "macos-x86_64",
        "macos-arm64",
        "windows",
    }


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


def test_cleanup_leaves_other_dotfiles_alone_when_enabled(
    tmp_path: pathlib.Path,
) -> None:
    # Matches mkdocs build --clean's own convention: a deployed .git
    # directory (or any other dotfile/dotdir) must survive the cleanup,
    # not just the one marker file.
    dot_dir = tmp_path / ".git"
    dot_dir.mkdir()
    (dot_dir / "config").write_text("stale")
    dot_file = tmp_path / ".gitignore"
    dot_file.write_text("stale")

    clean_viewer_server_layout(tmp_path, enabled=True)

    assert dot_dir.is_dir()
    assert (dot_dir / "config").is_file()
    assert dot_file.is_file()


def test_cleanup_leaves_other_dotfiles_alone_when_disabled(
    tmp_path: pathlib.Path,
) -> None:
    dot_dir = tmp_path / ".git"
    dot_dir.mkdir()
    dot_file = tmp_path / ".gitignore"
    dot_file.write_text("stale")

    clean_viewer_server_layout(tmp_path, enabled=False)

    assert dot_dir.is_dir()
    assert dot_file.is_file()


def test_copy_viewer_server_license_copies_content(tmp_path: pathlib.Path) -> None:
    source = tmp_path / "miniserve-LICENSE.txt"
    source.write_text("MIT License\n\nfake content")
    dest = tmp_path / "server" / "miniserve-LICENSE.txt"

    copy_viewer_server_license(source, dest)

    assert dest.is_file()
    assert dest.read_text() == source.read_text()


def test_copy_viewer_server_license_creates_destination_dir(
    tmp_path: pathlib.Path,
) -> None:
    source = tmp_path / "miniserve-LICENSE.txt"
    source.write_text("MIT License")
    dest = tmp_path / "nested" / "does" / "not" / "exist" / "miniserve-LICENSE.txt"

    copy_viewer_server_license(source, dest)

    assert dest.is_file()


def test_bundled_license_resource_file_matches_mit_text() -> None:
    import mkmapdiary

    resources_dir = pathlib.Path(mkmapdiary.__file__).parent / "resources"
    license_path = resources_dir / "viewer_server" / "miniserve-LICENSE.txt"
    content = license_path.read_text()
    assert "MIT License" in content
    assert "Sven-Hendrik Haase" in content
