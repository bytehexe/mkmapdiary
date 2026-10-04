import pathlib

from mkmapdiary.lib.dirs import Dirs
from mkmapdiary.tasks.siteTask import resolve_mkdocs_site_dir


def _make_dirs(tmp_path: pathlib.Path, bundle: bool) -> Dirs:
    dirs = Dirs(
        source_dir=tmp_path / "source",
        build_dir=tmp_path / "build",
        dist_dir=tmp_path / "dist",
        create_dirs=False,
    )
    dirs.bundle_viewer_server = bundle
    return dirs


def test_site_dir_is_dist_dir_when_not_bundling(tmp_path: pathlib.Path) -> None:
    dirs = _make_dirs(tmp_path, bundle=False)
    assert resolve_mkdocs_site_dir(dirs) == dirs.dist_dir


def test_site_dir_is_nested_site_when_bundling(tmp_path: pathlib.Path) -> None:
    dirs = _make_dirs(tmp_path, bundle=True)
    assert resolve_mkdocs_site_dir(dirs) == dirs.dist_dir / "_site"
