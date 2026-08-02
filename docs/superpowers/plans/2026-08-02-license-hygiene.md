# License Hygiene Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Credit dependencies on the docs site and in generated journals from data computed at build time, and remove the GPLv3 dependency that conflicts with mkmapdiary's license.

**Architecture:** A stdlib-only module `mkmapdiary/lib/credits.py` ships with the package and produces credit data three ways: by walking the installed dependency graph, by resolving from the package index, and by parsing CDN URLs out of `site_config.yaml`. The journal build calls it locally with no network; the docs build calls it through a mkdocs hook that imports it via `PYTHONPATH=src` without installing mkmapdiary. Nothing is committed to a data file, so nothing can go stale.

**Tech Stack:** Python 3.10+, doit, mkdocs + mkdocs-material, Jinja2, gettext, hatch, pytest, ruff, mypy.

**Spec:** `docs/superpowers/specs/2026-08-02-license-hygiene-design.md`

## Global Constraints

- `src/mkmapdiary/lib/credits.py` **must import only the standard library.** The docs hook imports it with only `src` on `PYTHONPATH`, so any third-party import breaks the docs build. A test enforces this.
- Type annotations are mandatory on every function — ruff `ANN` is enabled. `mypy` must pass via `hatch run types:check`.
- Ruff config: double quotes, magic trailing commas respected, `E501` (line length) ignored, `COM812` ignored.
- Commit messages follow Conventional Commits; `gitlint` runs in the `commit-msg` hook.
- No test may access the network.
- Run tests with `hatch test`. Run the full gate with `task test`.
- Python 3.10 is the floor: `datetime.date.fromisoformat` accepts only `YYYY-MM-DD` on 3.10 (relaxed in 3.11), so ISO parsing must assume the strict form.

---

### Task 1: Remove the GPLv3 tkcalendar dependency

The license conflict, and independent of everything else. `tkcalendar` is GPLv3; mkmapdiary is PolyForm Noncommercial, which imposes a field-of-use restriction that GPLv3 §7 forbids.

**Files:**
- Modify: `pyproject.toml:85-105` (the `ui` and `all` extras), `pyproject.toml` (`[tool.hatch.envs.licenses]`)
- Modify: `src/mkmapdiary/ui.py:22` (import), `src/mkmapdiary/ui.py:974-982` (widget)
- Test: `tests/test_ui_date_entry.py`

**Interfaces:**
- Consumes: nothing
- Produces: `mkmapdiary.ui.IsoDateEntry`, a `ttk.Entry` subclass with `get_date() -> datetime.date`

`ui.py:662` calls `self.calibrate_ref_date.get_date().strftime("%Y-%m-%d")`. That is tkcalendar's API, so the replacement must keep a `get_date()` returning `datetime.date` or line 662 breaks.

- [ ] **Step 1: Write the failing test**

Create `tests/test_ui_date_entry.py`:

```python
import datetime

import pytest

tk = pytest.importorskip("tkinter")


@pytest.fixture
def root() -> object:
    """A hidden Tk root, skipped when no display is available."""
    try:
        r = tk.Tk()
    except tk.TclError:
        pytest.skip("no display available")
    r.withdraw()
    yield r
    r.destroy()


def test_get_date_parses_iso(root: object) -> None:
    from mkmapdiary.ui import IsoDateEntry

    entry = IsoDateEntry(root)
    entry.delete(0, "end")
    entry.insert(0, "2026-08-02")

    assert entry.get_date() == datetime.date(2026, 8, 2)


def test_defaults_to_today(root: object) -> None:
    from mkmapdiary.ui import IsoDateEntry

    entry = IsoDateEntry(root)

    assert entry.get_date() == datetime.date.today()


def test_invalid_date_raises_value_error(root: object) -> None:
    from mkmapdiary.ui import IsoDateEntry

    entry = IsoDateEntry(root)
    entry.delete(0, "end")
    entry.insert(0, "not-a-date")

    with pytest.raises(ValueError):
        entry.get_date()
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `hatch test tests/test_ui_date_entry.py`
Expected: FAIL with `ImportError: cannot import name 'IsoDateEntry'`

- [ ] **Step 3: Add the widget and remove the tkcalendar import**

In `src/mkmapdiary/ui.py`, delete line 22 (`from tkcalendar import DateEntry`) and add `import datetime` to the stdlib imports at the top.

Add this class at module level, after the `capture_command_output` function:

```python
class IsoDateEntry(ttk.Entry):
    """A date entry accepting ISO dates (YYYY-MM-DD).

    Replaces tkcalendar.DateEntry, which is GPLv3 and therefore incompatible
    with mkmapdiary's PolyForm Noncommercial license. Keeps the get_date()
    interface so existing callers are unaffected.
    """

    def __init__(self, master: tk.Misc, **kwargs: Any) -> None:
        super().__init__(master, **kwargs)
        self.insert(0, datetime.date.today().isoformat())

    def get_date(self) -> datetime.date:
        """Return the entered date. Raises ValueError when malformed."""
        return datetime.date.fromisoformat(self.get().strip())
```

- [ ] **Step 4: Replace the widget construction**

Replace `src/mkmapdiary/ui.py:974-981` with:

```python
        self.calibrate_ref_date = IsoDateEntry(
            datetime_frame,
            width=12,
        )
```

Leave line 982 (`self.calibrate_ref_date.pack(...)`) unchanged.

- [ ] **Step 5: Handle a malformed date at the call site**

`get_date()` now raises on bad input, so `ui.py:662` needs a guard. Replace line 662 with:

```python
        try:
            ref_date = self.calibrate_ref_date.get_date().strftime("%Y-%m-%d")
        except ValueError:
            self.write_to_output(
                self.calibrate_output_text,
                "❌ Error: Please enter the date as YYYY-MM-DD",
                mode="replace",
            )
            self.calibrate_status_label.config(
                text="❌ Error", foreground=self.colors["error"]
            )
            return
```

This mirrors the existing validation block at lines 650-659.

- [ ] **Step 6: Remove tkcalendar from the extras**

In `pyproject.toml`, delete the `"tkcalendar",` line from both the `ui` extra (line 89) and the `all` extra (line 103). `babel` was pulled in only by tkcalendar and leaves with it — a grep confirms the only `babel` matches in the source tree are `gpsbabel`.

- [ ] **Step 7: Remove the now-unused licenses environment**

Delete this block from `pyproject.toml`:

```toml
[tool.hatch.envs.licenses]
extra-dependencies = [
  "pip-licenses",
]
```

It inherits `features = ["all"]`, so invoking it would build a second ~10 GB environment. `importlib.metadata` supersedes it.

- [ ] **Step 8: Run the tests**

Run: `hatch test tests/test_ui_date_entry.py`
Expected: PASS (or SKIP on a headless machine)

Run: `hatch run types:check`
Expected: no errors

- [ ] **Step 9: Verify tkcalendar is gone**

Run: `grep -rn "tkcalendar\|DateEntry" src/ pyproject.toml`
Expected: only matches for `IsoDateEntry`

- [ ] **Step 10: Commit**

```bash
git add pyproject.toml src/mkmapdiary/ui.py tests/test_ui_date_entry.py
git commit -m "fix: replace GPLv3 tkcalendar with an ISO date entry

tkcalendar is GPLv3, which conflicts with PolyForm Noncommercial: GPLv3
section 7 forbids the field-of-use restriction PolyForm imposes. The
dependency was used for a single date picker widget.

Also drop the licenses hatch env, which inherited features=[\"all\"] and
would have built a second ~10 GB environment."
```

---

### Task 2: Credits module core — license normalisation and the installed graph

**Files:**
- Create: `src/mkmapdiary/lib/credits.py`
- Test: `tests/test_credits.py`

**Interfaces:**
- Consumes: nothing
- Produces:
  - `Package` frozen dataclass with fields `name: str`, `version: str | None`, `license: str | None`, `url: str | None`
  - `canonical_name(name: str) -> str`
  - `normalise_license(metadata: Message, name: str) -> str | None`
  - `project_url(metadata: Message) -> str | None`
  - `installed_packages(root: str = "mkmapdiary") -> list[Package]`

Helpers take an `email.message.Message` rather than a `Distribution` so they are testable without installing anything.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_credits.py`:

```python
from email.message import Message

from mkmapdiary.lib.credits import (
    Package,
    canonical_name,
    installed_packages,
    normalise_license,
    project_url,
)


def _metadata(**fields: str | list[str]) -> Message:
    """Build a metadata Message; list values become repeated headers."""
    message = Message()
    for key, value in fields.items():
        header = key.replace("_", "-")
        if isinstance(value, list):
            for item in value:
                message.add_header(header, item)
        else:
            message.add_header(header, value)
    return message


def test_canonical_name_normalises_separators() -> None:
    assert canonical_name("PyExifTool") == "pyexiftool"
    assert canonical_name("mkdocs_material") == "mkdocs-material"
    assert canonical_name("zope.interface") == "zope-interface"


def test_license_expression_wins() -> None:
    md = _metadata(
        Name="poiidx",
        License_Expression="MIT",
        Classifier=["License :: OSI Approved :: BSD License"],
    )
    assert normalise_license(md, "poiidx") == "MIT"


def test_classifiers_used_when_no_expression() -> None:
    md = _metadata(
        Name="requests",
        Classifier=[
            "Programming Language :: Python",
            "License :: OSI Approved :: Apache Software License",
        ],
    )
    assert normalise_license(md, "requests") == "Apache Software License"


def test_multiple_classifiers_joined() -> None:
    md = _metadata(
        Name="tqdm",
        Classifier=[
            "License :: OSI Approved :: MIT License",
            "License :: OSI Approved :: Mozilla Public License 2.0 (MPL 2.0)",
        ],
    )
    assert normalise_license(md, "tqdm") == (
        "MIT License; Mozilla Public License 2.0 (MPL 2.0)"
    )


def test_short_license_field_used_as_fallback() -> None:
    md = _metadata(Name="peewee", License="MIT License")
    assert normalise_license(md, "peewee") == "MIT License"


def test_embedded_license_text_falls_through_to_none() -> None:
    md = _metadata(Name="obscure", License="Copyright 2026\n\nPermission is...")
    assert normalise_license(md, "obscure") is None


def test_dual_license_election_overrides_classifiers() -> None:
    """PyExifTool offers GPLv3+ or BSD; mkmapdiary elects BSD."""
    md = _metadata(
        Name="PyExifTool",
        License="GPLv3+/BSD",
        Classifier=[
            "License :: OSI Approved :: BSD License",
            "License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)",
        ],
    )
    assert normalise_license(md, "PyExifTool") == "BSD-3-Clause"


def test_project_url_prefers_home_page() -> None:
    md = _metadata(
        Name="x",
        Home_page="https://example.com",
        Project_URL=["Source, https://github.com/example/x"],
    )
    assert project_url(md) == "https://example.com"


def test_project_url_falls_back_to_labelled_entry() -> None:
    md = _metadata(
        Name="x",
        Project_URL=["Tracker, https://example.com/issues", "Source, https://example.com/x"],
    )
    assert project_url(md) == "https://example.com/x"


def test_project_url_missing_returns_none() -> None:
    assert project_url(_metadata(Name="x")) is None


def test_installed_packages_includes_root_and_excludes_strays() -> None:
    packages = installed_packages("mkmapdiary")
    names = {canonical_name(p.name) for p in packages}

    assert "mkmapdiary" in names
    assert "click" in names
    # pyinstaller may be present in the environment but is declared by nothing
    assert "pyinstaller" not in names


def test_installed_packages_returns_sorted_packages() -> None:
    packages = installed_packages("mkmapdiary")

    assert all(isinstance(p, Package) for p in packages)
    assert [p.name.lower() for p in packages] == sorted(p.name.lower() for p in packages)


def test_unknown_root_returns_empty() -> None:
    assert installed_packages("definitely-not-a-package") == []
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `hatch test tests/test_credits.py`
Expected: FAIL with `ModuleNotFoundError: No module named 'mkmapdiary.lib.credits'`

- [ ] **Step 3: Write the module**

Create `src/mkmapdiary/lib/credits.py`:

```python
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
    metadata = dist.metadata
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
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `hatch test tests/test_credits.py`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/mkmapdiary/lib/credits.py tests/test_credits.py
git commit -m "feat: add credits module with dependency graph traversal

Walks Requires-Dist outward from mkmapdiary so packages that are merely
installed do not appear as dependencies, and normalises licenses through
an election table that records the choice for dual-licensed packages."
```

---

### Task 3: Frontend libraries parsed from CDN URLs

**Files:**
- Modify: `src/mkmapdiary/lib/credits.py`
- Test: `tests/test_credits_frontend.py`

**Interfaces:**
- Consumes: `Package` from Task 2
- Produces:
  - `parse_cdn_url(url: str) -> tuple[str, str | None] | None` returning `(name, version)`
  - `frontend_libraries(site_config: Mapping[str, Any]) -> list[Package]`
  - `FRONTEND_LICENSES: dict[str, tuple[str, str]]` mapping canonical name to `(license, url)`

`extra_css` entries are plain strings; `extra_javascript` entries are dicts with a `path` key. Local paths such as `geo.js` are mkmapdiary's own and are skipped.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_credits_frontend.py`:

```python
from pathlib import Path
from typing import Any

import yaml

from mkmapdiary.lib.credits import (
    FRONTEND_LICENSES,
    canonical_name,
    frontend_libraries,
    parse_cdn_url,
)

SITE_CONFIG = (
    Path(__file__).parent.parent
    / "src"
    / "mkmapdiary"
    / "resources"
    / "site_config.yaml"
)


def test_parse_unpkg() -> None:
    assert parse_cdn_url("https://unpkg.com/leaflet@1.9.4/dist/leaflet.js") == (
        "leaflet",
        "1.9.4",
    )


def test_parse_unpkg_scoped_package() -> None:
    url = "https://unpkg.com/@lychee-org/leaflet.photo@1.0.0/Leaflet.Photo.css"
    assert parse_cdn_url(url) == ("@lychee-org/leaflet.photo", "1.0.0")


def test_parse_cdnjs() -> None:
    url = "https://cdnjs.cloudflare.com/ajax/libs/jquery/3.7.1/jquery.min.js"
    assert parse_cdn_url(url) == ("jquery", "3.7.1")


def test_parse_jsdelivr_npm_without_version() -> None:
    url = "https://cdn.jsdelivr.net/npm/justifiedGallery/dist/css/justifiedGallery.min.css"
    assert parse_cdn_url(url) == ("justifiedGallery", None)


def test_parse_jsdelivr_github() -> None:
    url = "https://cdn.jsdelivr.net/gh/iconoir-icons/iconoir@main/css/iconoir.css"
    assert parse_cdn_url(url) == ("iconoir-icons/iconoir", "main")


def test_local_path_is_not_a_cdn_url() -> None:
    assert parse_cdn_url("geo.js") is None


def test_frontend_libraries_from_site_config() -> None:
    config: dict[str, Any] = yaml.safe_load(SITE_CONFIG.read_text())
    libraries = frontend_libraries(config)

    names = {canonical_name(library.name) for library in libraries}
    assert "leaflet" in names
    assert "jquery" in names
    # mkmapdiary's own assets are not third-party credits
    assert not any(library.name.endswith(".js") for library in libraries)

    leaflet = next(lib for lib in libraries if canonical_name(lib.name) == "leaflet")
    assert leaflet.version == "1.9.4"
    assert leaflet.license is not None


def test_every_cdn_library_has_a_license_entry() -> None:
    """Staleness gate: adding a CDN library without crediting it fails here."""
    config: dict[str, Any] = yaml.safe_load(SITE_CONFIG.read_text())

    missing = []
    for library in frontend_libraries(config):
        if canonical_name(library.name) not in FRONTEND_LICENSES:
            missing.append(library.name)

    assert not missing, (
        f"Add these to FRONTEND_LICENSES in mkmapdiary/lib/credits.py: {missing}"
    )
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `hatch test tests/test_credits_frontend.py`
Expected: FAIL with `ImportError: cannot import name 'FRONTEND_LICENSES'`

- [ ] **Step 3: Add URL parsing and the license table**

Append to `src/mkmapdiary/lib/credits.py`:

```python
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
```

Extend the imports at the top of the module:

```python
from collections.abc import Iterator, Mapping
from typing import Any
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `hatch test tests/test_credits_frontend.py`
Expected: PASS

If `test_every_cdn_library_has_a_license_entry` fails, the failure message names the missing keys — add them to `FRONTEND_LICENSES` rather than loosening the test. Note that `canonical_name` collapses `.` to `-`, so `leaflet.markercluster` becomes `leaflet-markercluster`.

- [ ] **Step 5: Commit**

```bash
git add src/mkmapdiary/lib/credits.py tests/test_credits_frontend.py
git commit -m "feat: credit CDN libraries parsed from site_config

Name and version are read from the URL so they cannot drift from what the
page loads. A test asserts every CDN URL has a license table entry, so
adding a library without crediting it fails the suite."
```

---

### Task 4: Resolve packages from the index without installing

**Files:**
- Modify: `src/mkmapdiary/lib/credits.py`
- Create: `tests/fixtures/pip_report.json`
- Test: `tests/test_credits_resolve.py`

**Interfaces:**
- Consumes: `Package`, `normalise_license` from Task 2
- Produces:
  - `packages_from_report(report: Mapping[str, Any]) -> list[Package]`
  - `resolved_packages(spec: str = "mkmapdiary[all]") -> list[Package]`

`resolved_packages` shells out; `packages_from_report` is the pure part and is what the tests exercise. No test touches the network.

- [ ] **Step 1: Write the fixture**

Create `tests/fixtures/pip_report.json`, an abridged but structurally faithful pip report:

```json
{
  "version": "1",
  "install": [
    {
      "metadata": {
        "name": "click",
        "version": "8.1.7",
        "classifier": ["License :: OSI Approved :: BSD License"],
        "project_url": ["Source, https://github.com/pallets/click"]
      }
    },
    {
      "metadata": {
        "name": "poiidx",
        "version": "0.0.8",
        "license_expression": "MIT",
        "home_page": "https://github.com/bytehexe/poiidx"
      }
    },
    {
      "metadata": {
        "name": "PyExifTool",
        "version": "0.5.6",
        "license": "GPLv3+/BSD",
        "classifier": [
          "License :: OSI Approved :: BSD License",
          "License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)"
        ]
      }
    }
  ]
}
```

- [ ] **Step 2: Write the failing tests**

Create `tests/test_credits_resolve.py`:

```python
import json
from pathlib import Path
from typing import Any

from mkmapdiary.lib.credits import canonical_name, packages_from_report

REPORT = Path(__file__).parent / "fixtures" / "pip_report.json"


def _report() -> dict[str, Any]:
    return json.loads(REPORT.read_text())


def test_report_yields_all_packages() -> None:
    packages = packages_from_report(_report())

    assert {canonical_name(p.name) for p in packages} == {
        "click",
        "poiidx",
        "pyexiftool",
    }


def test_report_reads_versions() -> None:
    packages = {canonical_name(p.name): p for p in packages_from_report(_report())}

    assert packages["click"].version == "8.1.7"
    assert packages["poiidx"].version == "0.0.8"


def test_report_uses_the_same_license_rules_as_installed_metadata() -> None:
    packages = {canonical_name(p.name): p for p in packages_from_report(_report())}

    assert packages["poiidx"].license == "MIT"
    assert packages["click"].license == "BSD License"
    # the election table applies here too
    assert packages["pyexiftool"].license == "BSD-3-Clause"


def test_report_reads_urls() -> None:
    packages = {canonical_name(p.name): p for p in packages_from_report(_report())}

    assert packages["poiidx"].url == "https://github.com/bytehexe/poiidx"
    assert packages["click"].url == "https://github.com/pallets/click"


def test_empty_report_yields_nothing() -> None:
    assert packages_from_report({"install": []}) == []
```

- [ ] **Step 3: Run the tests to verify they fail**

Run: `hatch test tests/test_credits_resolve.py`
Expected: FAIL with `ImportError: cannot import name 'packages_from_report'`

- [ ] **Step 4: Implement report parsing and resolution**

Append to `src/mkmapdiary/lib/credits.py`:

```python
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


def resolved_packages(spec: str = "mkmapdiary[all]") -> list[Package]:
    """Resolve ``spec`` from the package index without installing it.

    PyPI serves PEP 658 metadata files, so pip fetches each wheel's METADATA
    rather than the wheel itself; resolving the torch stack costs kilobytes.

    Raises CalledProcessError when resolution fails, so a documentation build
    goes red rather than silently publishing an incomplete credits page.
    """
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "pip",
            "install",
            "--dry-run",
            "--ignore-installed",
            "--quiet",
            "--report",
            "-",
            spec,
        ],
        capture_output=True,
        check=True,
        text=True,
    )
    return packages_from_report(json.loads(completed.stdout))
```

Extend the imports at the top of the module:

```python
import json
import subprocess
import sys
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `hatch test tests/test_credits_resolve.py`
Expected: PASS

- [ ] **Step 6: Verify resolution works for real**

This step needs network and is a manual check, not a test:

Run: `hatch run python -c "import sys; sys.path.insert(0,'src'); from mkmapdiary.lib.credits import resolved_packages; p=resolved_packages(); print(len(p)); print(p[:3])"`
Expected: a package count in the low hundreds and three `Package` instances

If it is slow the first time, that is pip populating its HTTP cache.

- [ ] **Step 7: Commit**

```bash
git add src/mkmapdiary/lib/credits.py tests/test_credits_resolve.py tests/fixtures/pip_report.json
git commit -m "feat: resolve dependency credits without installing

Uses pip --dry-run --report so the docs build never installs torch, and
routes the result through the same license rules as installed metadata."
```

---

### Task 5: Configuration and translations

**Files:**
- Modify: `src/mkmapdiary/resources/defaults.yaml`, `src/mkmapdiary/resources/config_schema.yaml:236` (strings block), `src/mkmapdiary/locale/de/LC_MESSAGES/messages.po`, `src/mkmapdiary/locale/en/LC_MESSAGES/messages.po`
- Test: `tests/test_credits_config.py`

**Interfaces:**
- Consumes: nothing
- Produces: config key `credits.travellers` (list of strings, default `[]`) and the string keys `credits_title`, `credits_travellers`, `credits_made_with`, `credits_software`, `credits_toolchain`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_credits_config.py`:

```python
from pathlib import Path
from typing import Any

import pytest
from jsonschema.exceptions import ValidationError

from mkmapdiary.lib.config import load_config_data, load_config_file

RESOURCES = Path(__file__).parent.parent / "src" / "mkmapdiary" / "resources"

CREDITS_STRINGS = (
    "credits_title",
    "credits_travellers",
    "credits_made_with",
    "credits_software",
    "credits_toolchain",
)


def test_defaults_have_empty_travellers() -> None:
    config = load_config_file(RESOURCES / "defaults.yaml")

    assert config["credits"]["travellers"] == []


def test_defaults_declare_credits_strings() -> None:
    config = load_config_file(RESOURCES / "defaults.yaml")

    for key in CREDITS_STRINGS:
        assert key in config["strings"], key
        assert config["strings"][key] is None


def test_travellers_accepts_a_list_of_names() -> None:
    config: dict[str, Any] = {"credits": {"travellers": ["Janna Hopp", "Alex"]}}

    assert load_config_data(config)["credits"]["travellers"] == ["Janna Hopp", "Alex"]


def test_travellers_rejects_a_bare_string() -> None:
    with pytest.raises(ValidationError):
        load_config_data({"credits": {"travellers": "Janna Hopp"}})


def test_travellers_rejects_non_string_entries() -> None:
    with pytest.raises(ValidationError):
        load_config_data({"credits": {"travellers": [42]}})
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `hatch test tests/test_credits_config.py`
Expected: FAIL with `KeyError: 'credits'`

- [ ] **Step 3: Add the config defaults**

In `src/mkmapdiary/resources/defaults.yaml`, add a top-level block after `ignore_dates: []`:

```yaml
credits:
  # Names of the people who travelled; shown on the generated credits page
  travellers: []
```

and add these keys to the `strings:` block, alongside the existing `null` entries:

```yaml
  credits_title: null
  credits_travellers: null
  credits_made_with: null
  credits_software: null
  credits_toolchain: null
```

- [ ] **Step 4: Add the schema**

In `src/mkmapdiary/resources/config_schema.yaml`, add a top-level property beside `ignore_dates` (around line 228):

```yaml
  credits:
    type: object
    description: "Credits shown on the generated site"
    properties:
      travellers:
        type: array
        description: "Names of the people who travelled"
        items:
          type: string
    additionalProperties: false
```

and add the five string keys inside the `strings.properties` block (line 239 onward):

```yaml
      credits_title:
        $ref: "#/definitions/customString"
      credits_travellers:
        $ref: "#/definitions/customString"
      credits_made_with:
        $ref: "#/definitions/customString"
      credits_software:
        $ref: "#/definitions/customString"
      credits_toolchain:
        $ref: "#/definitions/customString"
```

- [ ] **Step 5: Add the translations**

Append to `src/mkmapdiary/locale/en/LC_MESSAGES/messages.po`:

```po
msgid "credits_title"
msgstr "Credits"

msgid "credits_travellers"
msgstr "Travellers"

msgid "credits_made_with"
msgstr "Made with"

msgid "credits_software"
msgstr "Open source software"

msgid "credits_toolchain"
msgstr "Built using more open source software than is listed here; the full list is in the mkmapdiary documentation."
```

Append to `src/mkmapdiary/locale/de/LC_MESSAGES/messages.po`:

```po
msgid "credits_title"
msgstr "Danksagungen"

msgid "credits_travellers"
msgstr "Reisende"

msgid "credits_made_with"
msgstr "Erstellt mit"

msgid "credits_software"
msgstr "Open-Source-Software"

msgid "credits_toolchain"
msgstr "Erstellt mit mehr Open-Source-Software als hier aufgeführt; die vollständige Liste steht in der mkmapdiary-Dokumentation."
```

- [ ] **Step 6: Regenerate the compiled translations**

Run: `task translate`
Expected: `messages.mo` rewritten for both languages

This is required — the `translation-files` pre-commit hook fails when the `.mo` files are stale.

- [ ] **Step 7: Run the tests**

Run: `hatch test tests/test_credits_config.py`
Expected: PASS

Run: `hatch test`
Expected: PASS — `tests/test_config.py` also validates the defaults file

- [ ] **Step 8: Commit**

```bash
git add src/mkmapdiary/resources/defaults.yaml src/mkmapdiary/resources/config_schema.yaml src/mkmapdiary/locale tests/test_credits_config.py
git commit -m "feat: add credits config and translation strings

A plain list of traveller names, plus the five strings the credits page
needs in German and English."
```

---

### Task 6: The journal credits page

**Files:**
- Create: `src/mkmapdiary/templates/credits.j2`
- Modify: `src/mkmapdiary/tasks/siteTask.py` (new task, `task_build_site` deps, `__simple_assets` untouched), `src/mkmapdiary/resources/site_config.yaml:19` (copyright)
- Test: `tests/test_credits_template.py`

**Interfaces:**
- Consumes: `installed_packages`, `frontend_libraries`, `Package` from Tasks 2-3; the config and strings from Task 5
- Produces: doit task `build_credits_page` writing `docs_dir/credits.md`

`use_directory_urls` is `False` in `site_config.yaml`, so the built page is `credits.html` at the site root and a relative link of `credits.html` works from every page.

- [ ] **Step 1: Write the failing test**

Create `tests/test_credits_template.py`:

```python
from typing import Any

from jinja2 import Environment, PackageLoader, StrictUndefined, select_autoescape

from mkmapdiary.lib.credits import Package

STRINGS = {
    "credits_title": "Credits",
    "credits_travellers": "Travellers",
    "credits_made_with": "Made with",
    "credits_software": "Open source software",
    "credits_toolchain": "Full list in the docs.",
}


def _render(**params: Any) -> str:
    env = Environment(
        loader=PackageLoader("mkmapdiary"),
        autoescape=select_autoescape(),
        undefined=StrictUndefined,
    )
    defaults: dict[str, Any] = {
        "travellers": [],
        "mkmapdiary_version": "1.2.3",
        "libraries": [],
        "docs_url": "https://bytehexe.github.io/mkmapdiary/reference/credits.html",
        "strings": STRINGS,
    }
    defaults.update(params)
    return env.get_template("credits.j2").render(**defaults)


def test_renders_travellers() -> None:
    output = _render(travellers=["Janna Hopp", "Alex"])

    assert "Travellers" in output
    assert "Janna Hopp" in output
    assert "Alex" in output


def test_omits_travellers_section_when_empty() -> None:
    output = _render(travellers=[])

    assert "Travellers" not in output


def test_always_credits_mkmapdiary_and_its_license() -> None:
    output = _render()

    assert "mkmapdiary" in output
    assert "1.2.3" in output
    assert "PolyForm Noncommercial" in output


def test_renders_libraries_with_versions_and_licenses() -> None:
    output = _render(
        libraries=[
            Package("leaflet", "1.9.4", "BSD-2-Clause", "https://leafletjs.com/"),
            Package("jquery", "3.7.1", "MIT", None),
        ],
    )

    assert "leaflet" in output
    assert "1.9.4" in output
    assert "BSD-2-Clause" in output
    assert "https://leafletjs.com/" in output
    # a library without a homepage still appears
    assert "jquery" in output


def test_links_to_the_docs_for_the_toolchain() -> None:
    output = _render()

    assert "https://bytehexe.github.io/mkmapdiary/reference/credits.html" in output
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `hatch test tests/test_credits_template.py`
Expected: FAIL with `jinja2.exceptions.TemplateNotFound: credits.j2`

- [ ] **Step 3: Write the template**

Create `src/mkmapdiary/templates/credits.j2`:

```jinja
# {{ strings.credits_title }}

{% if travellers %}
## {{ strings.credits_travellers }}

{{ travellers | join(", ") }}

{% endif %}
{# Photographers belong here once that feature lands. #}
## {{ strings.credits_made_with }}

[mkmapdiary](https://github.com/bytehexe/mkmapdiary) {{ mkmapdiary_version }} —
[PolyForm Noncommercial 1.0.0](https://polyformproject.org/licenses/noncommercial/1.0.0/)

{% if libraries %}
## {{ strings.credits_software }}

| Name | Version | License |
| --- | --- | --- |
{% for library in libraries -%}
| {% if library.url %}[{{ library.name }}]({{ library.url }}){% else %}{{ library.name }}{% endif %} | {{ library.version or "" }} | {{ library.license or "" }} |
{% endfor %}
{% endif %}
{{ strings.credits_toolchain }} [{{ docs_url }}]({{ docs_url }})
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `hatch test tests/test_credits_template.py`
Expected: PASS

- [ ] **Step 5: Add the doit task**

In `src/mkmapdiary/tasks/siteTask.py`, add these imports at the top:

```python
from mkmapdiary.lib.credits import (
    canonical_name,
    frontend_libraries,
    installed_packages,
)
```

Add this method to `SiteTask`, after `task_compile_css`:

```python
    # Packages whose *output* is copied into the built site. Metadata cannot
    # answer "does this end up in _dist", so the list is explicit.
    __bundled_packages = (
        "mkdocs-material",  # theme CSS/JS is compiled into the site
        "mkdocs-glightbox",  # lightbox assets are copied into the site
    )

    DOCS_CREDITS_URL = (
        "https://bytehexe.github.io/mkmapdiary/reference/credits.html"
    )

    @create_after("end_postprocessing")
    def task_build_credits_page(self) -> dict[str, Any]:
        """Generate the credits page for the journal."""

        def _generate() -> None:
            with open(
                self.dirs.resources_dir / "site_config.yaml",
            ) as site_config_file:
                site_config = yaml.safe_load(site_config_file)

            libraries = list(frontend_libraries(site_config))

            installed = {
                canonical_name(package.name): package
                for package in installed_packages()
            }
            for name in self.__bundled_packages:
                package = installed.get(name)
                if package is not None:
                    libraries.append(package)
                else:
                    logger.warning(f"Not installed, omitted from credits: {name}")

            libraries.sort(key=lambda package: package.name.lower())

            version = installed.get("mkmapdiary")
            content = self.template(
                "credits.j2",
                travellers=self.config["credits"]["travellers"],
                mkmapdiary_version=version.version if version else "",
                libraries=libraries,
                docs_url=self.DOCS_CREDITS_URL,
            )

            with open(self.dirs.docs_dir / "credits.md", "w") as credits_file:
                credits_file.write(content)

        return dict(
            actions=[(_generate, ())],
            targets=[self.dirs.docs_dir / "credits.md"],
            task_dep=[f"create_directory:{self.dirs.docs_dir}"],
            uptodate=[False],
        )
```

`BaseTask.template()` already passes `strings=self.config["strings"]`, so the template's `strings` variable is supplied automatically.

- [ ] **Step 6: Wire the page into the site build**

In `task_build_site`, add the page to the file dependencies. Inside `_generate_file_deps`, after the `index.md` line:

```python
            yield self.dirs.docs_dir / "credits.md"
```

and add `"build_credits_page"` to that task's `task_dep` list, after `"build_index_page"`.

Without both, mkdocs may run before the page exists.

- [ ] **Step 7: Link the page from the footer**

In `src/mkmapdiary/resources/site_config.yaml`, replace line 19:

```yaml
copyright: 'Created with <a href="https://github.com/bytehexe/mkmapdiary">mkmapdiary</a> — <a href="credits.html">Credits</a>'
```

- [ ] **Step 8: Build a real journal and check the page**

Run: `task demo`
Expected: the build completes

Run: `grep -A 5 "Made with" demo_dist/credits.html`
Expected: mkmapdiary, a version, and the PolyForm link

Open `demo_dist/credits.html` and confirm the footer link works and the software table is populated.

- [ ] **Step 9: Run the full suite**

Run: `hatch test`
Expected: PASS

Run: `hatch run types:check`
Expected: no errors

- [ ] **Step 10: Commit**

```bash
git add src/mkmapdiary/templates/credits.j2 src/mkmapdiary/tasks/siteTask.py src/mkmapdiary/resources/site_config.yaml tests/test_credits_template.py
git commit -m "feat: add a credits page to generated journals

Credits the travellers, mkmapdiary and its license, and the software the
built site actually ships or loads, with a link to the documentation for
the full Python toolchain. Data is read from the local environment, so
the build stays offline."
```

---

### Task 7: The docs credits page

**Files:**
- Create: `docs/reference/credits.md`, `docs/hooks/credits_table.py`
- Modify: `mkdocs.yml` (hooks), `docs/reference/index.md`, `.github/workflows/publish-docs.yml:19`, `pyproject.toml` (the `mkdocs:serve` script)
- Test: `tests/test_docs_credits_hook.py`

**Interfaces:**
- Consumes: `resolved_packages`, `Package` from Task 4
- Produces: `docs/hooks/credits_table.py` exposing `render_table(packages: list[Package]) -> str` and mkdocs' `on_page_markdown` hook

The hook imports `mkmapdiary.lib.credits` from the source tree via `PYTHONPATH`, so the docs CI never installs mkmapdiary. This works because `src/mkmapdiary/__init__.py` is empty and the module imports only the standard library.

- [ ] **Step 1: Write the failing test**

Create `tests/test_docs_credits_hook.py`:

```python
import subprocess
import sys
from pathlib import Path

from mkmapdiary.lib.credits import Package

ROOT = Path(__file__).parent.parent


def _load_hook() -> object:
    sys.path.insert(0, str(ROOT / "docs"))
    try:
        import hooks.credits_table as module
    finally:
        sys.path.pop(0)
    return module


def test_render_table_produces_a_markdown_table() -> None:
    module = _load_hook()

    table = module.render_table(
        [
            Package("click", "8.1.7", "BSD License", "https://palletsprojects.com/"),
            Package("poiidx", "0.0.8", "MIT", None),
        ],
    )

    assert "| Name | Version | License |" in table
    assert "[click](https://palletsprojects.com/)" in table
    assert "8.1.7" in table
    assert "poiidx" in table
    assert "MIT" in table


def test_render_table_handles_missing_fields() -> None:
    module = _load_hook()

    table = module.render_table([Package("mystery")])

    assert "mystery" in table


def test_credits_module_imports_with_only_src_on_the_path() -> None:
    """The docs build imports credits.py without installing mkmapdiary."""
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "import mkmapdiary.lib.credits as c; print(c.Package('x').name)",
        ],
        cwd=ROOT,
        env={"PYTHONPATH": "src", "PATH": ""},
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "x"
```

The third test is the guard for the stdlib-only constraint: it runs with an environment containing nothing but `PYTHONPATH=src`, so any third-party import fails it.

- [ ] **Step 2: Run the tests to verify they fail**

Run: `hatch test tests/test_docs_credits_hook.py`
Expected: FAIL with `ModuleNotFoundError: No module named 'hooks'`

- [ ] **Step 3: Write the hook**

Create `docs/hooks/__init__.py` (empty file), then `docs/hooks/credits_table.py`:

```python
"""Inject the dependency credits table into the docs at build time.

Imports mkmapdiary.lib.credits from the source tree, so the documentation
build never installs mkmapdiary or its dependencies.
"""

from typing import Any

from mkmapdiary.lib.credits import Package, resolved_packages

MARKER = "<!-- CREDITS_TABLE -->"


def render_table(packages: list[Package]) -> str:
    """Render packages as a markdown table."""
    rows = ["| Name | Version | License |", "| --- | --- | --- |"]
    for package in packages:
        if package.url:
            name = f"[{package.name}]({package.url})"
        else:
            name = package.name
        rows.append(f"| {name} | {package.version or ''} | {package.license or ''} |")
    return "\n".join(rows)


def on_page_markdown(
    markdown: str,
    page: Any = None,
    config: Any = None,
    files: Any = None,
) -> str:
    """Replace the marker with the generated table."""
    if MARKER not in markdown:
        return markdown

    # Deliberately unguarded: a failure here should fail the docs build rather
    # than publish a credits page that quietly lost its table.
    packages = resolved_packages()
    return markdown.replace(MARKER, render_table(packages))
```

- [ ] **Step 4: Register the hook**

In `mkdocs.yml`, add a top-level key:

```yaml
hooks:
  - docs/hooks/credits_table.py
```

The hook lives inside `docs/`, which is the `docs_dir`, so mkdocs would otherwise
copy its source into the published site. Extend the existing `exclude_docs` block:

```yaml
exclude_docs: |
  /superpowers/
  /hooks/
```

- [ ] **Step 5: Write the docs page**

Create `docs/reference/credits.md`:

```markdown
# Credits

## License

Mkmapdiary is distributed under the [PolyForm Noncommercial License 1.0.0](https://polyformproject.org/licenses/noncommercial/1.0.0/).

> Required Notice: Copyright Janna Hopp (https://github.com/bytehexe)

## poiidx

Point-of-interest indexing is provided by [poiidx](https://github.com/bytehexe/poiidx),
also by Janna Hopp, under the MIT license.

## Dependencies

Mkmapdiary is built on the following open source packages. This list is generated
when the documentation is built, by resolving `mkmapdiary[all]` against the package
index, so it always matches the current dependency set.

Attribution here is a courtesy rather than an obligation: the attribution clauses in
the MIT, BSD and Apache licenses attach to redistribution, and mkmapdiary does not
redistribute these packages — pip fetches each one from PyPI.

<!-- CREDITS_TABLE -->
```

- [ ] **Step 6: Link it from the reference index**

In `docs/reference/index.md`, add to the Development section:

```markdown
- **[Credits](credits.md)** - License and the open source packages mkmapdiary builds on
```

- [ ] **Step 7: Put src on the path for docs builds**

In `.github/workflows/publish-docs.yml`, change line 19 from:

```yaml
      - run: env PYTHONPATH=docs/ mkdocs build
```

to:

```yaml
      - run: env PYTHONPATH=src:docs/ mkdocs build
```

Leave the `pip install mkdocs mkdocs-material` line untouched — that is the point.

In `pyproject.toml`, change the mkdocs serve script to match:

```toml
serve = "PYTHONPATH=src:docs/ mkdocs serve --livereload"
```

- [ ] **Step 8: Build the docs and check the table**

Run: `hatch run mkdocs:serve` and open the credits page, or build once:

Run: `env PYTHONPATH=src:docs hatch run mkdocs:mkdocs build --strict`
Expected: build succeeds and `site/reference/credits/index.html` contains a populated table

This step needs network, since the hook resolves from the index.

- [ ] **Step 9: Run the tests**

Run: `hatch test tests/test_docs_credits_hook.py`
Expected: PASS

- [ ] **Step 10: Commit**

```bash
git add docs/reference/credits.md docs/reference/index.md docs/hooks mkdocs.yml .github/workflows/publish-docs.yml pyproject.toml tests/test_docs_credits_hook.py
git commit -m "feat: generate the docs credits page at build time

A mkdocs hook resolves mkmapdiary[all] from the index and injects the
dependency table, importing the credits module from src so CI still
installs only mkdocs and mkdocs-material."
```

---

### Task 8: Update the project documentation

**Files:**
- Modify: `CLAUDE.md`, `docs/reference/configuration.md`

**Interfaces:**
- Consumes: everything above
- Produces: nothing

- [ ] **Step 1: Document the config key**

In `docs/reference/configuration.md`, add `credits.travellers` to the configuration reference, following the surrounding style:

```yaml
credits:
  travellers:                              # Names shown on the credits page
    - Janna Hopp
    - Alex
```

- [ ] **Step 2: Document the module in CLAUDE.md**

In the "Cross-cutting concerns" section of `CLAUDE.md`, add:

```markdown
- **Credits**: `lib/credits.py` computes dependency credits at build time — never
  from a committed file. It must import **only the standard library**, because
  `docs/hooks/credits_table.py` imports it with just `src` on `PYTHONPATH` so the
  docs CI never installs mkmapdiary. `installed_packages()` walks the declared
  graph locally (offline, used by journals); `resolved_packages()` resolves from
  the index (used by the docs). CDN library licenses live in `FRONTEND_LICENSES`
  and a test asserts every URL in `site_config.yaml` has an entry.
```

- [ ] **Step 3: Run the full gate**

Run: `task test`
Expected: every hook passes

- [ ] **Step 4: Commit**

```bash
git add CLAUDE.md docs/reference/configuration.md
git commit -m "docs: document the credits config and module constraints"
```

---

## Notes for the implementer

**Ordering.** Task 1 is independent and resolves the license conflict, so do it first. Tasks 2-4 build the module bottom-up. Task 5 must precede Task 6, which reads the config it adds. Task 7 depends only on Tasks 2 and 4.

**The stdlib-only rule is load-bearing.** If `credits.py` grows a third-party import, `test_credits_module_imports_with_only_src_on_the_path` fails and the docs build breaks in CI. Reach for `email.message.Message` and `re` rather than `packaging`.

**Environment markers are ignored on purpose.** `_requirement_names` strips everything after `;`. A dependency behind an uninstalled extra fails the `distribution()` lookup and is skipped, which is what makes the journal page credit exactly what is installed.

**Do not add a committed credits data file.** It was considered and rejected: a snapshot goes stale silently, and stale credits are worse than no credits.

**`hatch run` eats curly braces.** It performs its own `{...}` substitution before the shell sees the command, so `hatch run python -c "print(f'{x}')"` fails with `Unknown context field 'x'`. Put throwaway scripts in a file and run `hatch run python path/to/script.py` instead.
