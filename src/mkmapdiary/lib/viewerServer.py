"""Download, checksum-verify, and cache the bundled viewer-server binaries.

Follows the same atomic download pattern as poiidx.Pbf: write to a temp file
in the cache directory, then os.replace into place, so an interrupted
download can't poison the cache for a later run. Unlike poiidx, nothing here
touches a database — this is pure binary fetch-and-cache.
"""

import hashlib
import logging
import os
import pathlib
import tempfile
import urllib.request

logger = logging.getLogger(__name__)

_MINISERVE_VERSION = "0.35.0"

# Pinned against GitHub's release API `digest` field for v0.35.0. Do not
# change without re-verifying against the new release's published digests.
MINISERVE_RELEASES: dict[str, tuple[str, str]] = {
    "linux": (
        f"https://github.com/svenstaro/miniserve/releases/download/v{_MINISERVE_VERSION}/miniserve-{_MINISERVE_VERSION}-x86_64-unknown-linux-gnu",
        "3b43ec6cb8ef5d5cc72a216b2309ef77c90952fd2c3e3c6eb9010dec39f3a086",
    ),
    "macos": (
        f"https://github.com/svenstaro/miniserve/releases/download/v{_MINISERVE_VERSION}/miniserve-{_MINISERVE_VERSION}-x86_64-apple-darwin",
        "63a99448bf7c450f1264a1af313646df30251bdbc3284b8f4d2d55cee2b98c55",
    ),
    "windows": (
        f"https://github.com/svenstaro/miniserve/releases/download/v{_MINISERVE_VERSION}/miniserve-{_MINISERVE_VERSION}-x86_64-pc-windows-msvc.exe",
        "3229e75b40b3870382d23c9a0ecec880b9bd5f6e49160ce602bb15d00f275b6a",
    ),
}

_BINARY_SUFFIX = {"linux": "", "macos": "", "windows": ".exe"}


class ChecksumMismatchError(Exception):
    """A downloaded binary's SHA256 didn't match its pinned checksum."""


def _download(url: str, dest: pathlib.Path) -> None:
    urllib.request.urlretrieve(url, dest)  # noqa: S310 - URL is our own pinned constant


class ViewerServerBinaries:
    def __init__(self, cache_dir: pathlib.Path) -> None:
        self.cache_dir = cache_dir

    def get_binary_path(self, platform: str) -> pathlib.Path:
        url, expected_sha256 = MINISERVE_RELEASES[platform]
        suffix = _BINARY_SUFFIX[platform]
        cached_path = (
            self.cache_dir / f"miniserve-{_MINISERVE_VERSION}-{platform}{suffix}"
        )

        if cached_path.is_file():
            logger.debug(f"Using cached viewer-server binary for {platform}")
            return cached_path

        logger.info(f"Downloading viewer-server binary for {platform} ...")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            dir=self.cache_dir,
            delete=False,
        ) as temp_file:
            temp_path = pathlib.Path(temp_file.name)

        try:
            _download(url, temp_path)
            actual_sha256 = hashlib.sha256(temp_path.read_bytes()).hexdigest()
            if actual_sha256 != expected_sha256:
                raise ChecksumMismatchError(
                    f"Checksum mismatch for {platform} viewer-server binary: "
                    f"expected {expected_sha256}, got {actual_sha256}",
                )
            temp_path.chmod(0o755)
            os.replace(temp_path, cached_path)
        finally:
            temp_path.unlink(missing_ok=True)

        return cached_path
