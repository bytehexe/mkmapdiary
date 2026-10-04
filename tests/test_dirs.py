import pathlib

from mkmapdiary.lib.dirs import Dirs


def _make_dirs(tmp_path: pathlib.Path) -> Dirs:
    return Dirs(
        source_dir=tmp_path / "source",
        build_dir=tmp_path / "build",
        dist_dir=tmp_path / "dist",
        create_dirs=False,
    )


def test_published_site_dir_is_dist_dir_when_not_bundling(
    tmp_path: pathlib.Path,
) -> None:
    dirs = _make_dirs(tmp_path)
    dirs.bundle_viewer_server = False
    assert dirs.published_site_dir == dirs.dist_dir


def test_published_site_dir_is_nested_when_bundling(tmp_path: pathlib.Path) -> None:
    dirs = _make_dirs(tmp_path)
    dirs.bundle_viewer_server = True
    assert dirs.published_site_dir == dirs.dist_dir / "_site"


def test_published_site_dir_defaults_to_dist_dir(tmp_path: pathlib.Path) -> None:
    dirs = _make_dirs(tmp_path)
    assert dirs.published_site_dir == dirs.dist_dir


def test_published_site_dir_is_created_when_create_dirs_enabled(
    tmp_path: pathlib.Path,
) -> None:
    dirs = _make_dirs(tmp_path)
    dirs.bundle_viewer_server = True
    dirs.create_dirs = True
    site_dir = dirs.published_site_dir
    assert site_dir.is_dir()


def test_dist_dir_marker_file_path(tmp_path: pathlib.Path) -> None:
    dirs = _make_dirs(tmp_path)
    assert dirs.dist_dir_marker_file == dirs.dist_dir / ".mkmapdiary_dist_dir"
