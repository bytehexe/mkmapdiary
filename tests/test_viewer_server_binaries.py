import hashlib
import pathlib
from unittest.mock import MagicMock, patch

import pytest

from mkmapdiary.lib.viewerServer import (
    ChecksumMismatchError,
    ViewerServerBinaries,
)

FAKE_CONTENT = b"fake miniserve binary contents"
FAKE_SHA256 = hashlib.sha256(FAKE_CONTENT).hexdigest()


def _fake_urlretrieve(url: str, path: pathlib.Path) -> None:
    pathlib.Path(path).write_bytes(FAKE_CONTENT)


@patch(
    "mkmapdiary.lib.viewerServer.MINISERVE_RELEASES",
    {"linux": ("https://example.invalid/bin", FAKE_SHA256)},
)
@patch("mkmapdiary.lib.viewerServer._download", side_effect=_fake_urlretrieve)
def test_downloads_and_caches_on_first_call(
    mock_download: MagicMock, tmp_path: pathlib.Path
) -> None:
    binaries = ViewerServerBinaries(cache_dir=tmp_path)
    result = binaries.get_binary_path("linux")
    assert result.is_file()
    assert result.read_bytes() == FAKE_CONTENT
    assert mock_download.call_count == 1


@patch(
    "mkmapdiary.lib.viewerServer.MINISERVE_RELEASES",
    {"linux": ("https://example.invalid/bin", FAKE_SHA256)},
)
@patch("mkmapdiary.lib.viewerServer._download", side_effect=_fake_urlretrieve)
def test_uses_cache_on_second_call(
    mock_download: MagicMock, tmp_path: pathlib.Path
) -> None:
    binaries = ViewerServerBinaries(cache_dir=tmp_path)
    binaries.get_binary_path("linux")
    binaries.get_binary_path("linux")
    assert mock_download.call_count == 1


@patch(
    "mkmapdiary.lib.viewerServer.MINISERVE_RELEASES",
    {"linux": ("https://example.invalid/bin", "0" * 64)},
)
@patch("mkmapdiary.lib.viewerServer._download", side_effect=_fake_urlretrieve)
def test_checksum_mismatch_is_rejected_and_not_cached(
    mock_download: MagicMock,
    tmp_path: pathlib.Path,
) -> None:
    binaries = ViewerServerBinaries(cache_dir=tmp_path)
    with pytest.raises(ChecksumMismatchError):
        binaries.get_binary_path("linux")
    assert list(tmp_path.iterdir()) == []  # no poisoned partial file left behind


def test_unknown_platform_raises_key_error(tmp_path: pathlib.Path) -> None:
    binaries = ViewerServerBinaries(cache_dir=tmp_path)
    with pytest.raises(KeyError):
        binaries.get_binary_path("amiga")
