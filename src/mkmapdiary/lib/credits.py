"""Credit data for mkmapdiary and its dependencies.

This module must import only the standard library: the documentation build
imports it with just ``src`` on ``PYTHONPATH``, without installing mkmapdiary.
"""

import dataclasses
import json
import logging
import re
import subprocess
import sys
from collections import deque
from collections.abc import Iterator, Mapping
from email.message import Message
from importlib.metadata import Distribution, PackageNotFoundError, distribution
from typing import Any, cast

logger = logging.getLogger(__name__)

# Dual-licensed packages offer a choice that metadata cannot express, so the
# choice is recorded here. Only genuine dual licenses belong in this table --
# never use it to paper over an unclear one.
ELECTED_LICENSES = {
    # "GPLv3+ or BSD" at the recipient's option; mkmapdiary elects BSD so that
    # no GPL terms attach. The wheel ships both COPYING.BSD and COPYING.GPL.
    "pyexiftool": "BSD-3-Clause",
}

_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*")
_SEPARATORS_RE = re.compile(r"[-_.]+")

_URL_LABELS = ("homepage", "source", "repository")


@dataclasses.dataclass(frozen=True)
class Package:
    """A creditable piece of software."""

    name: str
    version: str | None = None
    license: str | None = None
    url: str | None = None


def canonical_name(name: str) -> str:
    """Normalise a distribution name per PEP 503."""
    return _SEPARATORS_RE.sub("-", name).lower()


def normalise_license(metadata: Message, name: str) -> str | None:
    """Resolve a license identifier, first hit wins."""
    elected = ELECTED_LICENSES.get(canonical_name(name))
    if elected:
        return elected

    expression = (metadata.get("License-Expression") or "").strip()
    if expression:
        return expression

    classifiers = [
        classifier.split("::")[-1].strip()
        for classifier in metadata.get_all("Classifier") or []
        if classifier.startswith("License ::")
    ]
    if classifiers:
        return "; ".join(classifiers)

    raw = (metadata.get("License") or "").strip()
    if raw and "\n" not in raw and len(raw) <= 60:
        return raw

    return None


def project_url(metadata: Message) -> str | None:
    """Find a homepage, preferring Home-page over labelled Project-URL entries."""
    home_page = (metadata.get("Home-page") or "").strip()
    if home_page:
        return home_page

    for entry in metadata.get_all("Project-URL") or []:
        label, _, url = entry.partition(",")
        if label.strip().lower() in _URL_LABELS:
            return url.strip()

    return None


def _requirement_names(dist: Distribution) -> list[str]:
    """Extract distribution names from Requires-Dist entries.

    Environment markers are ignored deliberately: a dependency declared behind
    an extra that is not installed simply fails the lookup and is skipped, so
    the result is the intersection of what is declared and what is present.
    """
    names = []
    for requirement in dist.requires or []:
        head = requirement.split(";", 1)[0].strip()
        match = _NAME_RE.match(head)
        if match:
            names.append(match.group(0))
    return names


def _to_package(dist: Distribution) -> Package:
    # `Distribution.metadata` is typed as the `PackageMetadata` protocol, but
    # is an `email.message.Message` at runtime; normalise_license/project_url
    # take Message so they stay testable without importlib.metadata.
    metadata = cast(Message, dist.metadata)
    name = metadata.get("Name") or ""
    return Package(
        name=name,
        version=dist.version,
        license=normalise_license(metadata, name),
        url=project_url(metadata),
    )


def installed_packages(root: str = "mkmapdiary") -> list[Package]:
    """Walk the declared dependency graph outward from ``root``.

    Traversing declarations rather than listing the environment keeps packages
    that merely happen to be installed out of the result.
    """
    seen: set[str] = set()
    queue: deque[str] = deque([root])
    packages: list[Package] = []

    while queue:
        name = queue.popleft()
        key = canonical_name(name)
        if key in seen:
            continue
        seen.add(key)

        try:
            dist = distribution(name)
        except PackageNotFoundError:
            logger.debug(f"Not installed, skipping for credits: {name}")
            continue

        packages.append(_to_package(dist))
        queue.extend(_requirement_names(dist))

    return sorted(packages, key=lambda package: package.name.lower())


# Licenses for CDN-hosted libraries, which a URL cannot express. Keyed by the
# canonical name that parse_cdn_url() returns. The test
# test_every_cdn_library_has_a_license_entry guards this against site_config.yaml.
FRONTEND_LICENSES = {
    "leaflet": ("BSD-2-Clause", "https://leafletjs.com/"),
    "leaflet-markercluster": (
        "MIT",
        "https://github.com/Leaflet/Leaflet.markercluster",
    ),
    "@lychee-org/leaflet-photo": (
        "MIT",
        "https://github.com/lychee-org/Leaflet.Photo",
    ),
    "leaflet-awesome-markers": (
        "MIT",
        "https://github.com/lennardv2/Leaflet.awesome-markers",
    ),
    "leaflet-gpx": ("BSD-2-Clause", "https://github.com/mpetazzoni/leaflet-gpx"),
    "leaflet-gesture-handling": (
        "MIT",
        "https://github.com/elmarquis/Leaflet.GestureHandling",
    ),
    "leaflet-fullscreen": (
        "MIT",
        "https://github.com/brunob/leaflet.fullscreen",
    ),
    "jquery": ("MIT", "https://jquery.com/"),
    "justifiedgallery": ("MIT", "https://github.com/miromannino/Justified-Gallery"),
    "iconoir-icons/iconoir": ("MIT", "https://iconoir.com/"),
}

_CDN_PATTERNS = (
    re.compile(
        r"^https://unpkg\.com/(?P<name>@[^/@]+/[^/@]+|[^/@]+)(?:@(?P<version>[^/]+))?/",
    ),
    re.compile(
        r"^https://cdn\.jsdelivr\.net/npm/(?P<name>@[^/@]+/[^/@]+|[^/@]+)(?:@(?P<version>[^/]+))?/",
    ),
    re.compile(
        r"^https://cdn\.jsdelivr\.net/gh/(?P<name>[^/@]+/[^/@]+)(?:@(?P<version>[^/]+))?/",
    ),
    re.compile(
        r"^https://cdnjs\.cloudflare\.com/ajax/libs/(?P<name>[^/]+)/(?P<version>[^/]+)/",
    ),
)


def parse_cdn_url(url: str) -> tuple[str, str | None] | None:
    """Extract (name, version) from a CDN URL, or None for local paths."""
    for pattern in _CDN_PATTERNS:
        match = pattern.match(url)
        if match:
            return match.group("name"), match.group("version")
    return None


def _asset_urls(site_config: Mapping[str, Any]) -> Iterator[str]:
    for entry in site_config.get("extra_css") or []:
        yield entry
    for entry in site_config.get("extra_javascript") or []:
        # extra_javascript entries are mappings with a path key
        yield entry["path"] if isinstance(entry, Mapping) else entry


def frontend_libraries(site_config: Mapping[str, Any]) -> list[Package]:
    """Credit the CDN libraries a generated site loads.

    Name and version come from the URL, so they cannot drift from what the
    page actually loads; license and homepage come from FRONTEND_LICENSES.
    """
    found: dict[str, Package] = {}

    for url in _asset_urls(site_config):
        parsed = parse_cdn_url(url)
        if parsed is None:
            continue

        name, version = parsed
        key = canonical_name(name)
        if key in found:
            continue

        license_name, homepage = FRONTEND_LICENSES.get(key, (None, None))
        found[key] = Package(
            name=name,
            version=version,
            license=license_name,
            url=homepage,
        )

    return sorted(found.values(), key=lambda package: package.name.lower())


def _metadata_from_report_entry(entry: Mapping[str, Any]) -> Message:
    """Rebuild a metadata Message from a pip report entry.

    Reusing the Message shape means resolved packages go through exactly the
    same license and URL rules as installed ones.
    """
    metadata = Message()
    metadata.add_header("Name", entry.get("name", ""))

    expression = entry.get("license_expression")
    if expression:
        metadata.add_header("License-Expression", expression)

    raw = entry.get("license")
    if raw:
        metadata.add_header("License", raw)

    for classifier in entry.get("classifier") or []:
        metadata.add_header("Classifier", classifier)

    home_page = entry.get("home_page")
    if home_page:
        metadata.add_header("Home-page", home_page)

    for url in entry.get("project_url") or []:
        metadata.add_header("Project-URL", url)

    return metadata


def packages_from_report(report: Mapping[str, Any]) -> list[Package]:
    """Convert a `pip install --report` document into packages."""
    packages = []
    for item in report.get("install") or []:
        entry = item.get("metadata") or {}
        name = entry.get("name", "")
        if not name:
            continue
        metadata = _metadata_from_report_entry(entry)
        packages.append(
            Package(
                name=name,
                version=entry.get("version"),
                license=normalise_license(metadata, name),
                url=project_url(metadata),
            ),
        )

    return sorted(packages, key=lambda package: package.name.lower())


def resolved_packages(
    spec: str = ".[all]",
    allow_prerelease: bool = False,
) -> list[Package]:
    """Resolve ``spec`` from the package index without installing it.

    PyPI serves PEP 658 metadata files, so pip fetches each wheel's METADATA
    rather than the wheel itself; resolving the torch stack costs kilobytes.

    The default spec resolves the local checkout (``.``) rather than the
    published ``mkmapdiary`` name deliberately: the documentation build
    always runs from a repository checkout, so this documents the dependency
    set of the commit actually being built rather than the last release.
    It also means resolution works before any release has been published --
    a real constraint today, since PyPI currently has no stable mkmapdiary
    release.

    ``allow_prerelease`` adds pip's ``--pre`` flag, which is pip's own
    all-or-nothing switch: it opts every transitive dependency into
    pre-releases, not just the package named in ``spec``. It exists only to
    resolve a *published* name, e.g. ``resolved_packages("mkmapdiary[all]",
    allow_prerelease=True)`` -- currently the only way to resolve mkmapdiary
    from PyPI at all, since mkmapdiary itself has no stable release yet. It
    is a stopgap tied to that fact, not a permanent design choice: once a
    stable mkmapdiary release exists, resolving the published name should
    not need it.

    Raises CalledProcessError when resolution fails, so a documentation build
    goes red rather than silently publishing an incomplete credits page.
    """
    command = [
        sys.executable,
        "-m",
        "pip",
        "install",
        "--dry-run",
        "--ignore-installed",
        "--quiet",
        "--report",
        "-",
    ]
    if allow_prerelease:
        command.append("--pre")
    command.append(spec)

    completed = subprocess.run(
        command,
        capture_output=True,
        check=True,
        text=True,
    )
    return packages_from_report(json.loads(completed.stdout))
