import pathlib

from mkmapdiary.lib.dirs import Dirs


def _make_dirs(tmp_path: pathlib.Path) -> Dirs:
    return Dirs(
        source_dir=tmp_path / "source",
        build_dir=tmp_path / "build",
        dist_dir=tmp_path / "dist",
        create_dirs=False,
    )


def test_fresh_nonempty_directory_has_no_marker(tmp_path: pathlib.Path) -> None:
    dirs = _make_dirs(tmp_path)
    dirs.dist_dir.mkdir(parents=True)
    (dirs.dist_dir / "some_unrelated_file.txt").touch()
    assert not dirs.dist_dir_marker_file.is_file()


def test_marker_recognized_after_touch(tmp_path: pathlib.Path) -> None:
    dirs = _make_dirs(tmp_path)
    dirs.dist_dir.mkdir(parents=True)
    dirs.dist_dir_marker_file.touch()
    assert dirs.dist_dir_marker_file.is_file()


def test_marker_survives_regardless_of_bundle_viewer_server_flag(
    tmp_path: pathlib.Path,
) -> None:
    # The marker must identify "this is an mkmapdiary dist_dir" independent
    # of whether index.html lives at the top or under _site/ — that's the
    # whole point of not inferring ownership from index.html's location.
    dirs = _make_dirs(tmp_path)
    dirs.dist_dir.mkdir(parents=True)
    dirs.dist_dir_marker_file.touch()
    for flag in (True, False):
        dirs.bundle_viewer_server = flag
        assert dirs.dist_dir_marker_file.is_file()
