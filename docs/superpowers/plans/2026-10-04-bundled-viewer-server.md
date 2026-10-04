# Bundled Viewer Server Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Every generated mkmapdiary journal is viewable from a real `http://127.0.0.1` origin instead of `file://`, so the existing OpenStreetMap tile layer gets a valid `Referer` header and stops being blocked by OSM's tile usage policy — with zero setup required of the person viewing the journal, on Windows, macOS, or Linux.

**Architecture:** A new doit task downloads and checksum-verifies three platform builds of `miniserve` (a small MIT-licensed static file server) into mkmapdiary's own cache directory, then copies them plus three OS-labeled launcher scripts into every build's output. The existing flat site output moves under a `_site/` subdirectory so the top level only contains the launchers — but only when this feature is enabled; the flag is off by default-preserving when disabled. The launcher scripts pick a free port from a fixed candidate list, start the bundled server bound to `127.0.0.1` only, wait for it to accept connections, then open the system's default browser. This plan does **not** touch what URL the map tile layer points at — only how the page containing it is served.

**Tech Stack:** Python (doit tasks, `hashlib` for checksum verification, `urllib.request` for download), Bash (`Open on Linux.sh`, `Open on Mac.command`), Windows Batch + PowerShell (`Open on Windows.bat`).

**Spec:** `docs/superpowers/specs/2026-10-04-bundled-viewer-server-design.md`

## Global Constraints

- `miniserve` version pinned to `v0.35.0`. Checksums below are taken directly from GitHub's release API `digest` field for this exact version and must not be changed without re-verifying against a new release.
- Candidate ports (in order): `51342`, `51343`, `51344`, `51345`, `51346` — chosen from the IANA dynamic/private range (49152–65535) specifically to avoid common local dev-tool ports (`3000`, `5000`, `8000`, `8080`, `8888`, etc.).
- The bundled server must bind to `127.0.0.1` only, never `0.0.0.0` — this is private travel content and must not be reachable from the rest of the user's LAN.
- Config flag is `features.bundle_viewer_server.enabled`, following the existing `features.<name>.enabled` convention (see `poi_detection`, `llms`, `transcription` in `resources/config_schema.yaml` / `resources/defaults.yaml`). Default `true`.
- When the flag is `false`, build output must be byte-for-byte unchanged from current behavior: flat directory, `index.html` at the top, no launchers, no bundled binaries, no `_site/` subdirectory.
- `miniserve` is MIT licensed — safe to redistribute, but requires a credits-page attribution entry since it is now bundled inside every generated site (same obligation class as the `FRONTEND_LICENSES` entries in `lib/credits.py`), shown only in builds where it's actually bundled.
- `_site/` nesting must be computed once, centrally (a new `Dirs` property), never via a post-build move step.
- The existing `dist_dir`-not-empty safety check in `commands/build.py` must not infer ownership from `index.html`'s location (that check breaks once `index.html` can live under `_site/`); it must use a dedicated marker file, mirroring the existing `build_dir_marker_file` pattern.

## Review Focus

- **Checksum mismatch on a cached/downloaded `miniserve` binary** (corrupted download, tampered mirror, wrong file served) — must be rejected and never copied into build output; a reasonable person expects a build to fail loudly here, not silently ship a different binary than the pinned one.
- **Re-running a build with `features.bundle_viewer_server.enabled: false` after a previous build had it `true` (or vice versa) into the same persistent `dist_dir`** — must not leave stale launchers/`_site/` artifacts from the previous mode lying around next to the new mode's output.
- **All candidate ports already in use on the user's machine** — the launcher must fail with a clear, visible message naming the ports it tried, not hang or fail silently.
- **A second build into an existing, legitimately-mkmapdiary-built `dist_dir`** (the `-B` persistent-build-dir, re-run case) with the feature enabled — must be recognized as "safe to build into" by the marker-file check, not rejected as "not empty and doesn't look like ours."
- **A pre-existing, non-mkmapdiary directory accidentally pointed at as `dist_dir`** (e.g. a typo pointing at a populated folder) — must still be rejected by the safety check exactly as before, just via the marker file instead of `index.html`.

---

### Task 1: `Dirs` gains `published_site_dir` and `dist_dir_marker_file`

**Files:**
- Modify: `src/mkmapdiary/lib/dirs.py`
- Test: `tests/test_dirs.py` (new file — no existing test file for `Dirs`)

**Interfaces:**
- Produces: `Dirs.bundle_viewer_server: bool` (public mutable attribute, default `False`, same pattern as the existing `Dirs.create_dirs` attribute — set after config resolution, mirroring how `dirs.create_dirs = True` is set in `commands/build.py`).
- Produces: `Dirs.published_site_dir -> pathlib.Path` (property; `dist_dir` when `bundle_viewer_server` is `False`, `dist_dir / "_site"` when `True`; creates the directory when `create_dirs` is `True`, same as other `Dirs` directory properties).
- Produces: `Dirs.dist_dir_marker_file -> pathlib.Path` (property; `dist_dir / ".mkmapdiary_dist_dir"`, same shape as the existing `build_dir_marker_file`).

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_dirs.py
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `hatch test tests/test_dirs.py -v`
Expected: FAIL with `AttributeError: 'Dirs' object has no attribute 'bundle_viewer_server'` (or `published_site_dir`/`dist_dir_marker_file` not found).

- [ ] **Step 3: Implement `Dirs` changes**

In `src/mkmapdiary/lib/dirs.py`, add `self.bundle_viewer_server = False` to `__init__` (next to `self.create_dirs = create_dirs`), and add two new properties after `dist_dir`:

```python
    @property
    def published_site_dir(self) -> pathlib.Path:
        if self.bundle_viewer_server:
            site_path = self.dist_dir / "_site"
        else:
            site_path = self.dist_dir
        if self.create_dirs:
            site_path.mkdir(parents=True, exist_ok=True)
        return site_path
```

And after `build_dir_marker_file`:

```python
    @property
    def dist_dir_marker_file(self) -> pathlib.Path:
        marker_path = self.dist_dir / ".mkmapdiary_dist_dir"
        return marker_path
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `hatch test tests/test_dirs.py -v`
Expected: PASS (all 5 tests)

- [ ] **Step 5: Run mypy**

Run: `hatch run types:check`
Expected: no new errors

- [ ] **Step 6: Commit**

```bash
git add src/mkmapdiary/lib/dirs.py tests/test_dirs.py
git commit -m "feat: add Dirs.published_site_dir and dist_dir_marker_file"
```

---

### Task 2: Config schema and defaults for `features.bundle_viewer_server`

**Files:**
- Modify: `src/mkmapdiary/resources/config_schema.yaml`
- Modify: `src/mkmapdiary/resources/defaults.yaml`
- Test: `tests/test_credits_config.py` is unrelated; use existing schema-validation test pattern — check `tests/` for the config schema test file first; if none exists for this exact purpose, add `tests/test_config_schema_bundle_viewer_server.py`.

**Interfaces:**
- Produces: `config["features"]["bundle_viewer_server"]["enabled"]: bool`, resolvable through the existing `resolve_config()` / `resources/defaults.yaml` → schema validation pipeline (`lib/config.py`).

- [ ] **Step 1: Write the failing test**

```python
# tests/test_config_schema_bundle_viewer_server.py
from pathlib import Path

import jsonschema
import yaml

RESOURCES = Path(__file__).parent.parent / "src" / "mkmapdiary" / "resources"


def test_defaults_declare_bundle_viewer_server_enabled_true() -> None:
    with open(RESOURCES / "defaults.yaml") as f:
        defaults = yaml.safe_load(f)
    assert defaults["features"]["bundle_viewer_server"]["enabled"] is True


def test_defaults_validate_against_schema() -> None:
    with open(RESOURCES / "defaults.yaml") as f:
        defaults = yaml.safe_load(f)
    with open(RESOURCES / "config_schema.yaml") as f:
        schema = yaml.safe_load(f)
    jsonschema.validate(instance=defaults, schema=schema)


def test_schema_rejects_unknown_bundle_viewer_server_key() -> None:
    with open(RESOURCES / "config_schema.yaml") as f:
        schema = yaml.safe_load(f)
    instance = {"features": {"bundle_viewer_server": {"enabled": True, "bogus": 1}}}
    import pytest

    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(instance=instance, schema=schema)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `hatch test tests/test_config_schema_bundle_viewer_server.py -v`
Expected: FAIL — `KeyError: 'bundle_viewer_server'`

- [ ] **Step 3: Add the schema entry**

In `src/mkmapdiary/resources/config_schema.yaml`, inside `features.properties`, add (alongside `poi_detection`, `llms`, etc.):

```yaml
      bundle_viewer_server:
        type: object
        properties:
          enabled:
            type: boolean
            description: "Bundle a local static-file server and per-OS launchers into the build output, so the generated journal is served over http://127.0.0.1 instead of file:// (required for the OpenStreetMap tile layer's Referer check)."
        additionalProperties: false
```

- [ ] **Step 4: Add the default**

In `src/mkmapdiary/resources/defaults.yaml`, inside `features:`, add (alongside `poi_detection`, etc.):

```yaml
  bundle_viewer_server:
    enabled: true
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `hatch test tests/test_config_schema_bundle_viewer_server.py -v`
Expected: PASS (all 3 tests)

- [ ] **Step 6: Run the full schema/config test suite to check for regressions**

Run: `hatch test tests/test_credits_config.py tests/test_credits_resolve.py -v`
Expected: PASS (unchanged — confirms the new key doesn't break existing config resolution)

- [ ] **Step 7: Commit**

```bash
git add src/mkmapdiary/resources/config_schema.yaml src/mkmapdiary/resources/defaults.yaml tests/test_config_schema_bundle_viewer_server.py
git commit -m "feat: add features.bundle_viewer_server config option"
```

---

### Task 3: `commands/build.py` — marker-based dist_dir safety check, wire `Dirs.bundle_viewer_server`

**Files:**
- Modify: `src/mkmapdiary/commands/build.py:95-133`
- Test: `tests/test_build_dist_dir_marker.py` (new)

**Interfaces:**
- Consumes: `Dirs.dist_dir_marker_file` (Task 1), `Dirs.bundle_viewer_server` (Task 1), `config_data["features"]["bundle_viewer_server"]["enabled"]` (Task 2).
- Produces: nothing new consumed by later tasks — this is the CLI entry-point wiring.

The CLI `main()` function in `build.py` is integration-level, imperative wiring with no existing dedicated test file in this codebase (the analogous `build_dir_marker_file` check also has none) — this plan follows that established pattern rather than introducing CLI-level testing infrastructure that doesn't otherwise exist. Correctness of the marker-file check itself is covered by testing `Dirs.dist_dir_marker_file` directly (Task 1) plus the test below, which exercises the marker-file semantics the same way `build.py` will use them.

- [ ] **Step 1: Write the failing test (marker-file semantics, independent of the CLI)**

```python
# tests/test_build_dist_dir_marker.py
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `hatch test tests/test_build_dist_dir_marker.py -v`
Expected: PASS already for this specific test file, since Task 1 already implements `dist_dir_marker_file` — this step instead confirms the *existing* `build.py` logic still references `index.html`, which Step 3 will change. Verify by reading `commands/build.py:116-124` and confirming the condition still checks `(dist_dir / "index.html").is_file()` before Step 3.

- [ ] **Step 3: Update `commands/build.py`**

Replace the block at `commands/build.py:116-124`:

```python
    if (
        dist_dir.is_dir()
        and any(dist_dir.iterdir())
        and not (dist_dir / "index.html").is_file()
    ):
        logger.error(
            f"Error: Distribution directory '{dist_dir}' is not empty and does not contain an index.html file.",
        )
        sys.exit(1)
```

with:

```python
    if (
        dist_dir.is_dir()
        and any(dist_dir.iterdir())
        and not dirs.dist_dir_marker_file.is_file()
    ):
        logger.error(
            f"Error: Distribution directory '{dist_dir}' is not empty and does not contain a .mkmapdiary_dist_dir file.",
        )
        sys.exit(1)
```

Then, immediately after the existing `dirs.build_dir_marker_file.touch()` line (`commands/build.py:133`), add:

```python
    # Create dist directory marker file
    dirs.dist_dir_marker_file.touch()
```

Finally, wire the feature flag onto `dirs` right after `config_data` is resolved (`commands/build.py:62`, before the sanity checks that follow at line 85 onward — `dirs.bundle_viewer_server` must be set before `dirs.published_site_dir` is read by any later task, and setting it here, right next to where `config_data` becomes available, keeps the two together):

```python
    config_data: MutableMapping[str, Any] = resolve_config(dirs, params, debug_fast)

    dirs.bundle_viewer_server = config_data["features"]["bundle_viewer_server"]["enabled"]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `hatch test tests/test_build_dist_dir_marker.py -v`
Expected: PASS (all 3 tests)

- [ ] **Step 5: Run mypy and the full test suite**

Run: `hatch run types:check && hatch test -- -m "not slow"`
Expected: no new errors, no regressions

- [ ] **Step 6: Commit**

```bash
git add src/mkmapdiary/commands/build.py tests/test_build_dist_dir_marker.py
git commit -m "fix: identify dist_dir ownership by marker file, not index.html location"
```

---

### Task 4: `siteTask.py` — point the published site at `published_site_dir`

**Files:**
- Modify: `src/mkmapdiary/tasks/siteTask.py:142-150` (`__site_dirs`), `:179-188` (`task_generate_mkdocs_config`), `:499-512` (`task_pre_build_site`), `:514-554` (`task_build_site`)
- Test: `tests/test_site_task_published_dir.py` (new) — tests the pure logic extracted from the task bodies, following the codebase's existing pattern of testing extracted functions rather than `task_*` methods directly (see `credits_libraries`, `ai_disclosure_rows`, `merge_creators` in `siteTask.py`).

**Interfaces:**
- Consumes: `Dirs.published_site_dir` (Task 1).
- Produces: the `mkdocs.yml` `site_dir` key now points at `published_site_dir` instead of `dist_dir`; `sitemap.xml`'s task target moves accordingly.

This task changes four places in `siteTask.py` that currently read `self.dirs.dist_dir` to mean "where the finished site is written." Each is changed to `self.dirs.published_site_dir`, except the `__site_dirs` list, which needs **both** (the launchers need `dist_dir` to exist at the top level; mkdocs needs `published_site_dir` to exist to write into):

- [ ] **Step 1: Write a failing test for the `site_dir` config computation**

The `site_dir` computation inside `task_generate_mkdocs_config._generate_mkdocs_config` is a closure, not independently callable. Extract it into a small, pure, testable function first — this is the step that makes it testable at all, matching the existing pattern of factoring task logic into plain functions:

```python
# tests/test_site_task_published_dir.py
import pathlib

import pytest

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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `hatch test tests/test_site_task_published_dir.py -v`
Expected: FAIL — `ImportError: cannot import name 'resolve_mkdocs_site_dir'`

- [ ] **Step 3: Add `resolve_mkdocs_site_dir` and wire it in**

In `src/mkmapdiary/tasks/siteTask.py`, add a module-level function near the top (alongside `ai_disclosure_rows`, `credits_libraries`, `merge_creators`):

```python
def resolve_mkdocs_site_dir(dirs: "Dirs") -> pathlib.Path:
    """Where mkdocs actually writes the finished, browsable site.

    Separate from ``dirs.dist_dir``, which is the top-level output folder:
    when the viewer server is bundled, the site itself nests under
    ``dist_dir / "_site"`` so the top level holds only the launchers.
    """
    return dirs.published_site_dir
```

Add the import at the top of `siteTask.py`:

```python
from ..lib.dirs import Dirs
```

(Check first whether `Dirs` is already imported under a different alias in this file — it is not, per the current imports at `siteTask.py:1-30`, so this is a new import.)

Then update `__site_dirs` (`siteTask.py:142-150`) to include both directories:

```python
    @property
    def __site_dirs(self) -> list[pathlib.Path]:
        return [
            self.dirs.build_dir,
            self.dirs.assets_dir,
            self.dirs.docs_dir,
            self.dirs.dist_dir,
            self.dirs.published_site_dir,
            self.dirs.files_dir,
            self.dirs.templates_dir,
        ]
```

Update `task_generate_mkdocs_config` (`siteTask.py:179-188`) to use the new function:

```python
            try:
                config["docs_dir"] = str(
                    self.dirs.docs_dir.relative_to(self.dirs.build_dir),
                )
                config["site_dir"] = str(
                    resolve_mkdocs_site_dir(self.dirs).relative_to(
                        self.dirs.build_dir,
                        walk_up=True,
                    ),
                )
            except ValueError:
                config["docs_dir"] = str(self.dirs.docs_dir.absolute())
                config["site_dir"] = str(resolve_mkdocs_site_dir(self.dirs).absolute())
```

Update `task_pre_build_site` (`siteTask.py:499-512`) to also depend on the published site dir existing:

```python
    def task_pre_build_site(self) -> dict[str, Any]:
        # Ensure that the site directories exist
        return {
            "actions": None,
            "task_dep": [
                f"create_directory:{self.dirs.build_dir}",
                f"create_directory:{self.dirs.assets_dir}",
                f"create_directory:{self.dirs.docs_dir}",
                f"create_directory:{self.dirs.dist_dir}",
                f"create_directory:{self.dirs.published_site_dir}",
                f"create_directory:{self.dirs.files_dir}",
                f"create_directory:{self.dirs.templates_dir}",
                "geo_correlation",
            ],
        }
```

Update `task_build_site` (`siteTask.py:514-554`) — both the `task_dep` on `create_directory` and the `targets` for `sitemap.xml` now reference `published_site_dir`:

```python
        return dict(
            actions=[
                "mkdocs build --clean --config-file "
                + str(self.dirs.build_dir / "mkdocs.yml"),
            ],
            file_dep=list(_generate_file_deps()),
            task_dep=[
                f"create_directory:{self.dirs.published_site_dir}",
                "build_index_page",
                "build_credits_page",
                "generate_mkdocs_config",
                "compile_css",
                "build_day_page",
                "build_gallery",
                "build_journal",
                "build_tags",
                "geo_correlation",
                "pre_build_site",
            ],
            calc_dep=["get_gpx_deps"],
            targets=[
                self.dirs.published_site_dir / "sitemap.xml",
            ],
        )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `hatch test tests/test_site_task_published_dir.py -v`
Expected: PASS (both tests)

- [ ] **Step 5: Run mypy and the full test suite**

Run: `hatch run types:check && hatch test -- -m "not slow"`
Expected: no new errors, no regressions

- [ ] **Step 6: Manual smoke test**

Run: `task demo` (per `CLAUDE.md`, this is the one example build safe to run — test data only). Confirm the build succeeds with the new default (`features.bundle_viewer_server.enabled: true` from Task 2) and that `demo_dist/_site/index.html` exists (Task 5+6 haven't added the launchers yet, so the top level will just contain `_site/` at this point — that's expected and gets resolved once Task 6 lands).

- [ ] **Step 7: Commit**

```bash
git add src/mkmapdiary/tasks/siteTask.py tests/test_site_task_published_dir.py
git commit -m "feat: write the published site under Dirs.published_site_dir"
```

---

### Task 5: `lib/viewerServer.py` — download, checksum-verify, and cache the `miniserve` binaries

**Files:**
- Create: `src/mkmapdiary/lib/viewerServer.py`
- Test: `tests/test_viewer_server_binaries.py`

**Interfaces:**
- Produces: `ViewerServerBinaries(cache_dir: pathlib.Path)` with method `get_binary_path(platform: str) -> pathlib.Path`, where `platform` is one of `"linux"`, `"macos"`, `"windows"`. Raises `ChecksumMismatchError` (new exception, also defined in this module) if a downloaded file doesn't match its pinned checksum.
- Produces: module-level constant `MINISERVE_RELEASES: dict[str, tuple[str, str]]` mapping platform name to `(download_url, sha256_hex)`.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_viewer_server_binaries.py
import hashlib
import pathlib
from unittest.mock import patch

import pytest

from mkmapdiary.lib.viewerServer import (
    ChecksumMismatchError,
    ViewerServerBinaries,
)

FAKE_CONTENT = b"fake miniserve binary contents"
FAKE_SHA256 = hashlib.sha256(FAKE_CONTENT).hexdigest()


def _fake_urlretrieve(url: str, path: pathlib.Path) -> None:
    pathlib.Path(path).write_bytes(FAKE_CONTENT)


@patch("mkmapdiary.lib.viewerServer.MINISERVE_RELEASES", {"linux": ("https://example.invalid/bin", FAKE_SHA256)})
@patch("mkmapdiary.lib.viewerServer._download", side_effect=_fake_urlretrieve)
def test_downloads_and_caches_on_first_call(mock_download, tmp_path: pathlib.Path) -> None:
    binaries = ViewerServerBinaries(cache_dir=tmp_path)
    result = binaries.get_binary_path("linux")
    assert result.is_file()
    assert result.read_bytes() == FAKE_CONTENT
    assert mock_download.call_count == 1


@patch("mkmapdiary.lib.viewerServer.MINISERVE_RELEASES", {"linux": ("https://example.invalid/bin", FAKE_SHA256)})
@patch("mkmapdiary.lib.viewerServer._download", side_effect=_fake_urlretrieve)
def test_uses_cache_on_second_call(mock_download, tmp_path: pathlib.Path) -> None:
    binaries = ViewerServerBinaries(cache_dir=tmp_path)
    binaries.get_binary_path("linux")
    binaries.get_binary_path("linux")
    assert mock_download.call_count == 1


@patch("mkmapdiary.lib.viewerServer.MINISERVE_RELEASES", {"linux": ("https://example.invalid/bin", "0" * 64)})
@patch("mkmapdiary.lib.viewerServer._download", side_effect=_fake_urlretrieve)
def test_checksum_mismatch_is_rejected_and_not_cached(
    mock_download, tmp_path: pathlib.Path,
) -> None:
    binaries = ViewerServerBinaries(cache_dir=tmp_path)
    with pytest.raises(ChecksumMismatchError):
        binaries.get_binary_path("linux")
    assert list(tmp_path.iterdir()) == []  # no poisoned partial file left behind


def test_unknown_platform_raises_key_error(tmp_path: pathlib.Path) -> None:
    binaries = ViewerServerBinaries(cache_dir=tmp_path)
    with pytest.raises(KeyError):
        binaries.get_binary_path("amiga")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `hatch test tests/test_viewer_server_binaries.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'mkmapdiary.lib.viewerServer'`

- [ ] **Step 3: Implement `lib/viewerServer.py`**

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `hatch test tests/test_viewer_server_binaries.py -v`
Expected: PASS (all 4 tests)

- [ ] **Step 5: Run mypy and ruff**

Run: `hatch run types:check && hatch run ruff:ruff check src/mkmapdiary/lib/viewerServer.py`
Expected: no errors

- [ ] **Step 6: Commit**

```bash
git add src/mkmapdiary/lib/viewerServer.py tests/test_viewer_server_binaries.py
git commit -m "feat: add download/cache/checksum-verify for bundled miniserve binaries"
```

---

### Task 6: Launcher script resources

**Files:**
- Create: `src/mkmapdiary/resources/viewer_server/Open on Linux.sh`
- Create: `src/mkmapdiary/resources/viewer_server/Open on Mac.command`
- Create: `src/mkmapdiary/resources/viewer_server/Open on Windows.bat`

These are static resource files (not generated per-build from a template — the port list and server binary name are fixed constants shared across every journal, so there's nothing build-specific to inject). They get copied verbatim into each build's output by Task 7.

**Interfaces:**
- Consumes: nothing from earlier tasks (pure static content).
- Produces: three files that Task 7 copies into `dist_dir` by name.

- [ ] **Step 1: Write `Open on Linux.sh`**

```bash
#!/bin/sh
# Starts the bundled viewer server and opens this journal in your browser.
# Close this terminal window to stop viewing.
set -eu

cd "$(dirname "$0")"

PORTS="51342 51343 51344 51345 51346"
PORT=""
for candidate in $PORTS; do
    if ! (exec 3<>"/dev/tcp/127.0.0.1/$candidate") 2>/dev/null; then
        PORT="$candidate"
        break
    fi
    exec 3>&- 3<&- 2>/dev/null || true
done

if [ -z "$PORT" ]; then
    echo "Could not find a free port among: $PORTS"
    echo "Close whatever is using one of these ports and try again."
    exit 1
fi

./_site/.server/miniserve-linux -i 127.0.0.1 -p "$PORT" --index index.html --disable-indexing ./_site &
SERVER_PID=$!
trap 'kill "$SERVER_PID" 2>/dev/null || true' EXIT

for _ in $(seq 1 50); do
    if (exec 3<>"/dev/tcp/127.0.0.1/$PORT") 2>/dev/null; then
        exec 3>&- 3<&- 2>/dev/null || true
        break
    fi
    sleep 0.1
done

URL="http://127.0.0.1:$PORT/"
xdg-open "$URL" >/dev/null 2>&1 || echo "Open this URL in your browser: $URL"

echo "Your travel journal is running at $URL"
echo "Close this window to stop viewing."
wait "$SERVER_PID"
```

- [ ] **Step 2: Write `Open on Mac.command`**

```bash
#!/bin/bash
# Starts the bundled viewer server and opens this journal in your browser.
# Close this terminal window to stop viewing.
set -eu

cd "$(dirname "$0")"

PORTS="51342 51343 51344 51345 51346"
PORT=""
for candidate in $PORTS; do
    if ! nc -z 127.0.0.1 "$candidate" 2>/dev/null; then
        PORT="$candidate"
        break
    fi
done

if [ -z "$PORT" ]; then
    echo "Could not find a free port among: $PORTS"
    echo "Close whatever is using one of these ports and try again."
    exit 1
fi

chmod +x ./_site/.server/miniserve-macos
./_site/.server/miniserve-macos -i 127.0.0.1 -p "$PORT" --index index.html --disable-indexing ./_site &
SERVER_PID=$!
trap 'kill "$SERVER_PID" 2>/dev/null || true' EXIT

for _ in $(seq 1 50); do
    if nc -z 127.0.0.1 "$PORT" 2>/dev/null; then
        break
    fi
    sleep 0.1
done

URL="http://127.0.0.1:$PORT/"
open "$URL" >/dev/null 2>&1 || echo "Open this URL in your browser: $URL"

echo "Your travel journal is running at $URL"
echo "Close this window to stop viewing."
wait "$SERVER_PID"
```

- [ ] **Step 3: Write `Open on Windows.bat`**

```batch
@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"

set PORT=
for %%P in (51342 51343 51344 51345 51346) do (
    if not defined PORT (
        powershell -NoProfile -Command "try { $c = New-Object System.Net.Sockets.TcpClient('127.0.0.1', %%P); $c.Close(); exit 1 } catch { exit 0 }" >nul 2>&1
        if !errorlevel! equ 0 (
            set PORT=%%P
        )
    )
)

if not defined PORT (
    echo Could not find a free port among: 51342 51343 51344 51345 51346
    echo Close whatever is using one of these ports and try again.
    pause
    exit /b 1
)

start "" /b ".\_site\.server\miniserve-windows.exe" -i 127.0.0.1 -p !PORT! --index index.html --disable-indexing .\_site

powershell -NoProfile -Command "for ($i=0; $i -lt 50; $i++) { try { $c = New-Object System.Net.Sockets.TcpClient('127.0.0.1', !PORT!); $c.Close(); exit 0 } catch { Start-Sleep -Milliseconds 100 } }"

set URL=http://127.0.0.1:!PORT!/
start "" "!URL!"

echo Your travel journal is running at !URL!
echo Close this window to stop viewing.
pause >nul
taskkill /f /im miniserve-windows.exe >nul 2>&1
```

- [ ] **Step 4: Make the shell scripts executable in git**

```bash
chmod +x "src/mkmapdiary/resources/viewer_server/Open on Linux.sh"
chmod +x "src/mkmapdiary/resources/viewer_server/Open on Mac.command"
```

- [ ] **Step 5: Syntax-check the shell scripts**

Run: `bash -n "src/mkmapdiary/resources/viewer_server/Open on Linux.sh" && bash -n "src/mkmapdiary/resources/viewer_server/Open on Mac.command"`
Expected: no output (no syntax errors). There is no equivalent static syntax checker available in this project's toolchain for `.bat` — note this in the PR description as something that needs a manual run on a real Windows machine before release (see Task 7, Step 6).

- [ ] **Step 6: Commit**

```bash
git add "src/mkmapdiary/resources/viewer_server/"
git commit -m "feat: add per-OS launcher scripts for the bundled viewer server"
```

---

### Task 7: Doit tasks — fetch binaries, copy into output, render launchers

**Files:**
- Modify: `src/mkmapdiary/tasks/siteTask.py`
- Test: `tests/test_viewer_server_task.py`

**Interfaces:**
- Consumes: `ViewerServerBinaries` (Task 5), `Dirs.bundle_viewer_server` / `Dirs.published_site_dir` / `Dirs.user_cache_dir` (Task 1), launcher resource files (Task 6).
- Produces: doit tasks `fetch_viewer_server_binaries` and `bundle_viewer_server`, gated on `config["features"]["bundle_viewer_server"]["enabled"]`.

- [ ] **Step 1: Write the failing test for the gating logic**

The task-generation logic that decides *whether* to emit the bundling steps is extracted into a plain function so it's testable without instantiating the full `TaskList`/doit machinery — following the same pattern as `credits_libraries`:

```python
# tests/test_viewer_server_task.py
from mkmapdiary.tasks.siteTask import viewer_server_platform_files


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
    by_launcher = {f.launcher_name: f.platform for f in files}
    assert by_launcher["Open on Linux.sh"] == "linux"
    assert by_launcher["Open on Mac.command"] == "macos"
    assert by_launcher["Open on Windows.bat"] == "windows"
```

And, in the same file, tests for the stale-layout cleanup (Step 3b below) — these call the extracted pure function directly rather than the doit task, same pattern as the rest of this file:

```python
import pathlib

from mkmapdiary.tasks.siteTask import clean_viewer_server_layout


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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `hatch test tests/test_viewer_server_task.py -v`
Expected: FAIL — `ImportError: cannot import name 'viewer_server_platform_files'`

- [ ] **Step 3: Implement the task logic in `siteTask.py`**

Add near the top of `siteTask.py`, alongside the other module-level helper functions:

```python
import dataclasses as _dc


@_dc.dataclass(frozen=True)
class _ViewerServerPlatformFile:
    launcher_name: str
    platform: str
    binary_name: str


def viewer_server_platform_files() -> list["_ViewerServerPlatformFile"]:
    return [
        _ViewerServerPlatformFile("Open on Linux.sh", "linux", "miniserve-linux"),
        _ViewerServerPlatformFile("Open on Mac.command", "macos", "miniserve-macos"),
        _ViewerServerPlatformFile(
            "Open on Windows.bat",
            "windows",
            "miniserve-windows.exe",
        ),
    ]
```

(Note: `_dc` import as a separate alias avoids colliding with the existing `import dataclasses` at the top of `siteTask.py` used by `task_build_index_page` — check `siteTask.py:1` first; if `dataclasses` is already imported unaliased there, as it is per the current file, reuse that same import instead of adding `_dc`, i.e. write `@dataclasses.dataclass(frozen=True)` and drop the `import dataclasses as _dc` line.)

Then add two new task methods to the `SiteTask` class, near `task_copy_simple_asset`:

```python
    def task_fetch_viewer_server_binaries(self) -> Iterator[dict[str, Any]]:
        from mkmapdiary.lib.viewerServer import MINISERVE_RELEASES, ViewerServerBinaries

        if not self.config["features"]["bundle_viewer_server"]["enabled"]:
            return

        binaries = ViewerServerBinaries(cache_dir=self.dirs.user_cache_dir / "viewer_server")

        for platform_file in viewer_server_platform_files():

            def _fetch(platform: str = platform_file.platform) -> pathlib.Path:
                return binaries.get_binary_path(platform)

            _, expected_checksum = MINISERVE_RELEASES[platform_file.platform]

            yield dict(
                name=platform_file.platform,
                actions=[(_fetch, ())],
                uptodate=[True],  # cache correctness is handled inside ViewerServerBinaries
                # No file_dep/targets: the cached binary lives outside dirs.build_dir
                # (in the user cache dir), so doit's dep tracking doesn't apply here
                # the way it does for build-local outputs. The checksum check inside
                # ViewerServerBinaries.get_binary_path is what guards correctness.
            )

    def task_bundle_viewer_server(self) -> Iterator[dict[str, Any]]:
        from mkmapdiary.lib.viewerServer import ViewerServerBinaries

        if not self.config["features"]["bundle_viewer_server"]["enabled"]:
            return

        binaries = ViewerServerBinaries(cache_dir=self.dirs.user_cache_dir / "viewer_server")
        # published_site_dir is dist_dir / "_site" whenever this task runs at
        # all (it's gated on the same flag that makes published_site_dir
        # nest), so this is simply the .server/ subdirectory inside it.
        server_dir = self.dirs.published_site_dir / ".server"
        launcher_resources_dir = self.dirs.resources_dir / "viewer_server"

        def _copy_binary(platform_file: "_ViewerServerPlatformFile") -> None:
            server_dir.mkdir(parents=True, exist_ok=True)
            source = binaries.get_binary_path(platform_file.platform)
            dest = server_dir / platform_file.binary_name
            shutil.copy2(source, dest)
            dest.chmod(0o755)

        def _copy_launcher(platform_file: "_ViewerServerPlatformFile") -> None:
            source = launcher_resources_dir / platform_file.launcher_name
            dest = self.dirs.dist_dir / platform_file.launcher_name
            shutil.copy2(source, dest)
            dest.chmod(0o755)

        for platform_file in viewer_server_platform_files():
            yield dict(
                name=f"binary:{platform_file.platform}",
                actions=[(_copy_binary, (platform_file,))],
                task_dep=[
                    f"fetch_viewer_server_binaries:{platform_file.platform}",
                    f"create_directory:{self.dirs.published_site_dir}",
                ],
                targets=[server_dir / platform_file.binary_name],
                uptodate=[False],
            )
            yield dict(
                name=f"launcher:{platform_file.platform}",
                actions=[(_copy_launcher, (platform_file,))],
                file_dep=[launcher_resources_dir / platform_file.launcher_name],
                task_dep=[f"create_directory:{self.dirs.dist_dir}"],
                targets=[self.dirs.dist_dir / platform_file.launcher_name],
            )
```

Finally, add `"bundle_viewer_server"` to `task_build_site`'s `task_dep` list (`siteTask.py`, the block updated in Task 4) so the launchers/binaries are present whenever the site is built with the feature on — append it after `"pre_build_site"`.

- [ ] **Step 3b: Implement and wire the stale-layout cleanup**

A persistent `dist_dir` rebuilt with the flag flipped from its last value would otherwise accumulate stale artifacts: leftover launchers/`_site/.server` when switching off (nothing deletes them), or a leftover top-level `index.html`/`credits.html`/`sitemap.xml`/`assets/` from a prior non-bundled build when switching on (`mkdocs build --clean` only cleans inside `site_dir`, i.e. `published_site_dir` — it never touches siblings sitting directly in `dist_dir`). Add a pure, testable cleanup function and a doit task that always runs (not gated on the flag, since it must react to *either* direction of change):

```python
def clean_viewer_server_layout(dist_dir: pathlib.Path, *, enabled: bool) -> None:
    """Remove whichever layout doesn't match the current bundle_viewer_server value.

    Keeps dist_dir consistent across a persistent build directory being
    rebuilt with the flag flipped from its previous value. Never touches
    .mkmapdiary_dist_dir (Task 3) or the entries that belong to the current
    mode.
    """
    if not dist_dir.is_dir():
        return

    launcher_names = {f.launcher_name for f in viewer_server_platform_files()}

    if enabled:
        for entry in dist_dir.iterdir():
            if entry.name in launcher_names or entry.name == "_site":
                continue
            if entry.name == ".mkmapdiary_dist_dir":
                continue
            if entry.is_dir():
                shutil.rmtree(entry)
            else:
                entry.unlink()
    else:
        for name in launcher_names:
            stale_launcher = dist_dir / name
            if stale_launcher.is_file():
                stale_launcher.unlink()
        stale_site = dist_dir / "_site"
        if stale_site.is_dir():
            shutil.rmtree(stale_site)
```

Add the corresponding doit task to `SiteTask`, near `task_bundle_viewer_server`:

```python
    def task_clean_viewer_server_layout(self) -> dict[str, Any]:
        enabled = self.config["features"]["bundle_viewer_server"]["enabled"]
        dist_dir = self.dirs.dist_dir

        return dict(
            actions=[(clean_viewer_server_layout, (dist_dir,), {"enabled": enabled})],
            task_dep=[f"create_directory:{self.dirs.dist_dir}"],
            uptodate=[False],
        )
```

Add `"clean_viewer_server_layout"` to `task_pre_build_site`'s `task_dep` list (the block updated in Task 4), before the other site-building task deps, so cleanup always happens before mkdocs runs or the launchers/binaries get copied in.

- [ ] **Step 4: Run tests to verify they pass**

Run: `hatch test tests/test_viewer_server_task.py -v`
Expected: PASS (all 6 tests: 2 from Step 1, 4 from the cleanup block added above)

- [ ] **Step 5: Run mypy and the full test suite**

Run: `hatch run types:check && hatch test -- -m "not slow"`
Expected: no new errors, no regressions

- [ ] **Step 6: Manual smoke test — full build with and without the feature**

Run: `task demo` (default config, feature on by default per Task 2). Confirm:
- `demo_dist/` top level contains `Open on Linux.sh`, `Open on Mac.command`, `Open on Windows.bat`, and `_site/`.
- `demo_dist/_site/.server/` contains all three binaries, each executable.
- `demo_dist/_site/index.html` exists.

Then run again with `-x features.bundle_viewer_server.enabled=false` and confirm `demo_dist/` is flat — `index.html` at the top, no launchers, no `_site/`, no `.server/` — matching current behavior exactly.

Then, on this machine (Linux), actually run `./Open on Linux.sh` from inside `demo_dist/` and confirm: a free port is found, the server starts bound to `127.0.0.1`, the browser opens to the journal, and closing the terminal (or Ctrl+C) stops the server. The macOS and Windows launchers need the equivalent manual check on those platforms before this is considered done — flag this explicitly as outstanding in the PR description, since this environment can't run them.

- [ ] **Step 7: Commit**

```bash
git add src/mkmapdiary/tasks/siteTask.py tests/test_viewer_server_task.py
git commit -m "feat: wire up doit tasks to fetch and bundle the viewer server"
```

---

### Task 8: Credits/attribution entry for the bundled `miniserve` binary

**Files:**
- Modify: `src/mkmapdiary/lib/credits.py`
- Modify: `src/mkmapdiary/tasks/siteTask.py` (`task_build_credits_page`, `__ai_disclosure`-adjacent credits assembly)
- Test: `tests/test_credits_bundled_binaries.py`

**Interfaces:**
- Consumes: `Package` dataclass (existing, `lib/credits.py:37`), `config["features"]["bundle_viewer_server"]["enabled"]`.
- Produces: `bundled_binary_credits(enabled: bool) -> list[Package]` in `lib/credits.py`, included in the credits page only for builds where the feature is actually on — following the existing "driven by what a build actually generated" principle already used for AI disclosure rows (`CLAUDE.md`, "AI transparency").

- [ ] **Step 1: Write the failing test**

```python
# tests/test_credits_bundled_binaries.py
from mkmapdiary.lib.credits import bundled_binary_credits


def test_includes_miniserve_when_enabled() -> None:
    result = bundled_binary_credits(enabled=True)
    names = {package.name for package in result}
    assert "miniserve" in names


def test_empty_when_disabled() -> None:
    assert bundled_binary_credits(enabled=False) == []


def test_miniserve_entry_has_license_and_homepage() -> None:
    result = bundled_binary_credits(enabled=True)
    miniserve = next(p for p in result if p.name == "miniserve")
    assert miniserve.license == "MIT"
    assert miniserve.url == "https://github.com/svenstaro/miniserve"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `hatch test tests/test_credits_bundled_binaries.py -v`
Expected: FAIL — `ImportError: cannot import name 'bundled_binary_credits'`

- [ ] **Step 3: Implement `bundled_binary_credits` in `lib/credits.py`**

Add near `FRONTEND_LICENSES` (`lib/credits.py:149-178`):

```python
# Binaries bundled directly into generated output (not resolved from pip or
# a CDN URL, so neither installed_packages() nor FRONTEND_LICENSES covers
# them). Only shown on the credits page for builds that actually bundle
# them — see bundled_binary_credits().
BUNDLED_BINARY_LICENSES: dict[str, tuple[str, str]] = {
    "miniserve": ("MIT", "https://github.com/svenstaro/miniserve"),
}


def bundled_binary_credits(enabled: bool) -> list[Package]:
    """Credits entries for binaries bundled directly into build output.

    ``enabled`` reflects whether this specific build actually bundled them
    (``features.bundle_viewer_server.enabled``), not whether the feature
    exists in general — a build that didn't bundle the server shouldn't
    claim credit for shipping it.
    """
    if not enabled:
        return []
    return [
        Package(name=name, version=None, license=license_name, url=url)
        for name, (license_name, url) in BUNDLED_BINARY_LICENSES.items()
    ]
```

Check `Package`'s exact field names/types first (`lib/credits.py:37-45`) before writing this — if `version` is not `Optional`, adjust accordingly (likely `version: str | None = None` already, matching how `installed_packages` entries without a resolvable version would behave; confirm against the existing dataclass definition rather than assuming).

- [ ] **Step 4: Wire it into the credits page assembly**

In `siteTask.py`'s `task_build_credits_page` → `_generate()` (`siteTask.py:432-461`), extend the `libraries` list:

```python
            libraries = credits_libraries(
                site_config,
                installed,
                self.__bundled_packages,
            )
            libraries.extend(
                bundled_binary_credits(
                    enabled=self.config["features"]["bundle_viewer_server"]["enabled"],
                ),
            )
            libraries.sort(key=lambda package: package.name.lower())
```

Add `bundled_binary_credits` to the existing import block at the top of `siteTask.py`:

```python
from mkmapdiary.lib.credits import (
    Package,
    bundled_binary_credits,
    canonical_name,
    frontend_libraries,
    installed_packages,
)
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `hatch test tests/test_credits_bundled_binaries.py -v`
Expected: PASS (all 3 tests)

- [ ] **Step 6: Run the full credits test suite and mypy**

Run: `hatch run types:check && hatch test tests/test_credits_libraries.py tests/test_credits_template.py tests/test_credits_bundled_binaries.py -v`
Expected: PASS, no regressions

- [ ] **Step 7: Manual check — credits page actually renders the entry**

Run: `task demo`, then check `demo_dist/_site/credits.html` (or `demo_dist/credits.html` if the feature was off in that run) contains "miniserve" and "MIT".

- [ ] **Step 8: Commit**

```bash
git add src/mkmapdiary/lib/credits.py src/mkmapdiary/tasks/siteTask.py tests/test_credits_bundled_binaries.py
git commit -m "feat: add credits entry for the bundled miniserve binary"
```

---

### Task 9: Task-dependency documentation update

**Files:**
- Modify: `docs/reference/task-dependencies.md`
- Modify: `docs/reference/task-dependencies.puml`

**Interfaces:**
- Consumes: nothing (documentation only).
- Produces: nothing consumed by other tasks — this is the project's required doc-sync step for any task-graph change (per `CLAUDE.md`: "Update `docs/reference/task-dependencies.md` ... when you add or rewire a task").

- [ ] **Step 1: Read the current diagram and doc**

Read `docs/reference/task-dependencies.puml` and `docs/reference/task-dependencies.md` in full to find where `build_site`, `pre_build_site`, `generate_mkdocs_config`, and `copy_simple_asset` are documented, matching their existing style exactly.

- [ ] **Step 2: Add the two new tasks**

In `task-dependencies.puml`, add `fetch_viewer_server_binaries` and `bundle_viewer_server` nodes, with `bundle_viewer_server` depending on `fetch_viewer_server_binaries` and `create_directory`, and `build_site` depending on `bundle_viewer_server` (matching the `task_dep` wiring added in Task 7, Step 3).

In `task-dependencies.md`, add prose entries for both tasks in the same section/style as the existing entries for `copy_simple_asset` and `pre_build_site`, noting they're no-ops (yield nothing) when `features.bundle_viewer_server.enabled` is `false`.

- [ ] **Step 3: Render and visually check the diagram**

Run: `hatch run mkdocs:serve` (per `CLAUDE.md`, the `mkdocs` env is `detached` and faithfully mirrors the docs CI job) and visually confirm the PlantUML diagram renders without errors and shows the new nodes in the expected position.

- [ ] **Step 4: Commit**

```bash
git add docs/reference/task-dependencies.md docs/reference/task-dependencies.puml
git commit -m "docs: add bundle_viewer_server tasks to the task dependency graph"
```

---

## Final verification (after all tasks)

- [ ] Run the full gate: `task test`
- [ ] Run `task demo` twice in a row (second run tests the persistent-build-dir re-run path) and confirm no stale files from a previous run's mode (on/off) leak into the new run's output — this is the "re-running with the flag flipped" Review Focus item; if `task demo` doesn't use a persistent dist dir by default, use `hatch run mkmapdiary build demo demo_dist -B` with `-x features.bundle_viewer_server.enabled=true` then `=false` against the same `demo_dist`, and inspect the result by hand.
- [ ] Confirm the macOS and Windows launcher scripts on real hardware (flagged as outstanding from Task 7 — this environment can only verify the Linux one).
