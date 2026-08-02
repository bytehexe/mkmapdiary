"""Credit data for mkmapdiary and its dependencies.

This module must import only the standard library: the documentation build
imports it with just ``src`` on ``PYTHONPATH``, without installing mkmapdiary.
"""

import dataclasses
import logging
import re
from collections import deque
from email.message import Message
from importlib.metadata import Distribution, PackageNotFoundError, distribution
from typing import cast

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
