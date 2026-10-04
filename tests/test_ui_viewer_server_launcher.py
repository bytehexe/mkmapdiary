"""Tests for viewer_server_launcher_path -- which launcher (if any) the GUI offers.

No tkinter import here, deliberately: see tests/test_ui_iso_date.py for why
importing mkmapdiary.ui itself is safe without a display.
"""

import pathlib

import pytest

from mkmapdiary.ui import viewer_server_launcher_path


def test_returns_linux_launcher_when_present(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("mkmapdiary.ui.platform.system", lambda: "Linux")
    launcher = tmp_path / "Open on Linux.sh"
    launcher.touch()

    assert viewer_server_launcher_path(tmp_path) == launcher


def test_returns_mac_launcher_when_present(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("mkmapdiary.ui.platform.system", lambda: "Darwin")
    launcher = tmp_path / "Open on Mac.command"
    launcher.touch()

    assert viewer_server_launcher_path(tmp_path) == launcher


def test_returns_windows_launcher_when_present(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("mkmapdiary.ui.platform.system", lambda: "Windows")
    launcher = tmp_path / "Open on Windows.bat"
    launcher.touch()

    assert viewer_server_launcher_path(tmp_path) == launcher


def test_returns_none_for_unrecognized_platform(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("mkmapdiary.ui.platform.system", lambda: "FreeBSD")
    (tmp_path / "Open on Linux.sh").touch()

    assert viewer_server_launcher_path(tmp_path) is None


def test_returns_none_when_launcher_file_missing(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("mkmapdiary.ui.platform.system", lambda: "Linux")

    assert viewer_server_launcher_path(tmp_path) is None
