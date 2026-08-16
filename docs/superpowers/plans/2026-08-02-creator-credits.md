# Creator Credits Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Attribute journal media to the people who made it — per-directory via the calibration stack, with an EXIF fallback, a general credit in config, a conditional per-asset attribution, and a combined section on the credits page.

**Architecture:** `Calibration` and `AssetRecord` each gain a `creator` field. The calibration stack resolves it per directory exactly as it resolves `effects`; images additionally fall back to `EXIF:Artist`. Display is conditional on the journal containing more than one distinct creator value. The credits page unions config creators, asset creators and GPX track creators into one deduplicated list.

**Tech Stack:** Python 3.12, doit, Jinja2, pydantic dataclasses, jsonschema, click, gettext, pytest, hatch.

## Global Constraints

- **Never run `pip`/`venv`.** All commands go through hatch: `hatch test`, `hatch run types:check`, `hatch run ruff:ruff check .`, `task fix`, `task test`.
- **Commits are GPG-signed.** Always commit with the sandbox disabled (`dangerouslyDisableSandbox: true`). Never use `--no-gpg-sign`.
- **Conventional Commits** enforced by gitlint; allowed prefixes in `docs/reference/development/commit-prefixes.md`.
- **Do not run the examples** (`task example`). If a real build is needed, ask Janna. `task demo` is the only exception.
- **Never stage with `git add -A` / `git add .`** — stage explicit paths.
- After touching any `.po` file, run `task translate` or pre-commit fails.
- Template tests use `StrictUndefined`, so every new template variable must be passed by every render site — production and test.
- No `ai_label.j2` anywhere in this work. Creator attribution is human authorship; the AI transparency rule covers machine-generated output only.
- German string for `credits_creators` is exactly `Urheber*innen`. English is exactly `Creators`.

---

## Spec Corrections

Three claims in `docs/superpowers/specs/2026-08-02-creator-credits-design.md` did not survive contact with the code. This plan implements the corrected versions; the spec is amended in Task 9.

1. **GPX.** The spec says `gpxTask.py:132` gains `creator=calibration.creator`. It cannot: `handle_gpx` (`gpxTask.py:35`) yields *no* assets, and the only GPX `AssetRecord` is built inside a doit action at `gpxTask.py:128` where no `Calibration` is in scope — and it is a *merged per-date* file that may combine sources from directories with different creators. Task 4 instead collects creators from GPX *source* files into a `track_creators` property (mirroring the existing `track_statistics` property) which feeds the credits page only.
2. **Templates.** The spec says two templates carry the metadata line. There are **three**: `day_journal.j2:12-16`, `day_gallery.j2:80-85`, and `index.j2:10-14`.
3. **`asdict`.** The spec says creator reaches the templates for free via `dataclasses.asdict`. True for `galleryTask.py:45` and `siteTask.py:232`, but **not** `journalTask.py:60-70`, which builds its item dict field by field. Task 5 adds the field explicitly there.

---

## File Structure

**Created**

| File | Responsibility |
| --- | --- |
| `tests/test_creator_calibration.py` | Calibration resolution and inheritance |
| `tests/test_creator_exif.py` | EXIF artist tag extraction |
| `tests/test_creator_registry.py` | `distinct_creators` and the visibility threshold |
| `tests/test_creator_templates.py` | The three metadata-line templates |
| `tests/test_creator_command.py` | `mkmapdiary calibrate creator` |

**Modified**

| File | Change |
| --- | --- |
| `src/mkmapdiary/lib/calibration.py` | `creator` field; new `resolve()` function |
| `src/mkmapdiary/lib/asset.py` | `creator` field on `AssetRecord` |
| `src/mkmapdiary/resources/calibrate_schema.yaml` | `creator` key, `anyOf` branch |
| `src/mkmapdiary/taskList.py` | `__push_calibration` delegates to `resolve()` |
| `src/mkmapdiary/tasks/base/exifReader.py` | `ExifData.artist`, `artist_from_exif()` |
| `src/mkmapdiary/tasks/{image,markdown,text,audio,rawInput}Task.py` | propagate creator |
| `src/mkmapdiary/tasks/gpxTask.py` | `track_creators` property |
| `src/mkmapdiary/tasks/galleryTask.py` | pass `show_creators` |
| `src/mkmapdiary/tasks/journalTask.py` | `creator` in item dict; pass `show_creators` |
| `src/mkmapdiary/tasks/siteTask.py` | abstract `track_creators`; `merge_creators()`; pass `show_creators`, `creators` |
| `src/mkmapdiary/tasks/base/baseTask.py` | `show_creators` property |
| `src/mkmapdiary/lib/assetRegistry.py` | `distinct_creators()` |
| `src/mkmapdiary/commands/calibrate.py` | `creator` subcommand |
| `src/mkmapdiary/templates/{index,day_gallery,day_journal,credits}.j2` | render creator |
| `src/mkmapdiary/resources/defaults.yaml` | `credits.creators`, `strings.credits_creators` |
| `src/mkmapdiary/resources/config_schema.yaml` | both of the above |
| `src/mkmapdiary/locale/{de,en}/LC_MESSAGES/messages.po` | `credits_creators` |
| `src/mkmapdiary/resources/extra.sass` | caption wrap fix (Task 8) |
| `docs/reference/configuration.md`, `CLAUDE.md` | documentation |

---

### Task 1: Calibration carries a creator

**Files:**
- Modify: `src/mkmapdiary/lib/calibration.py`
- Modify: `src/mkmapdiary/lib/asset.py:48`
- Modify: `src/mkmapdiary/resources/calibrate_schema.yaml`
- Modify: `src/mkmapdiary/taskList.py:212-233`
- Test: `tests/test_creator_calibration.py`

**Interfaces:**
- Consumes: nothing.
- Produces: `Calibration(timezone, offset, effects, creator)`; `mkmapdiary.lib.calibration.resolve(data: dict[str, Any], parent: Calibration) -> Calibration`; `AssetRecord.creator: str | None`.

The inheritance logic currently sits inline in the private `__push_calibration`, which makes it untestable without a filesystem. Move it into a pure `resolve()` function in `lib/calibration.py` and have `__push_calibration` call it.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_creator_calibration.py
from typing import Any

from mkmapdiary.lib.asset import AssetRecord
from mkmapdiary.lib.calibration import Calibration, resolve

PARENT = Calibration(timezone="UTC", offset=0, effects=[], creator="Janna")


def test_creator_defaults_to_none() -> None:
    assert Calibration(timezone="UTC", offset=0).creator is None


def test_asset_record_carries_a_creator() -> None:
    from pathlib import PosixPath

    asset = AssetRecord(path=PosixPath("x.jpg"), type="image", creator="Bob")
    assert asset.creator == "Bob"
    assert AssetRecord(path=PosixPath("y.jpg"), type="image").creator is None


def test_omitted_creator_is_inherited() -> None:
    data: dict[str, Any] = {"calibration": {"timezone": "UTC", "offset": 0}}
    assert resolve(data, PARENT).creator == "Janna"


def test_creator_can_be_overridden() -> None:
    assert resolve({"creator": "Bob"}, PARENT).creator == "Bob"


def test_explicit_null_clears_an_inherited_creator() -> None:
    """Distinct from omitting the key, which inherits."""
    assert resolve({"creator": None}, PARENT).creator is None


def test_resolve_still_inherits_timezone_offset_and_effects() -> None:
    parent = Calibration(
        timezone="Europe/Berlin", offset=42, effects=["autorotate"], creator="Janna"
    )
    result = resolve({"creator": "Bob"}, parent)

    assert result.timezone == "Europe/Berlin"
    assert result.offset == 42
    assert result.effects == ["autorotate"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `hatch test tests/test_creator_calibration.py -v`
Expected: FAIL with `ImportError: cannot import name 'resolve'`.

- [ ] **Step 3: Add the field and the resolve function**

```python
# src/mkmapdiary/lib/calibration.py
from typing import Any, NamedTuple


class Calibration(NamedTuple):
    timezone: str
    offset: int
    effects: list[str] = []
    creator: str | None = None


def resolve(data: dict[str, Any], parent: Calibration) -> Calibration:
    """Resolve a calibration.yaml payload against the enclosing calibration.

    Keys absent from `data` are inherited from `parent`. A key present with a
    null value is an explicit override, not an inheritance — that is how a
    subdirectory clears a creator it would otherwise inherit.
    """
    calibration = data.get("calibration", {})
    return Calibration(
        timezone=calibration.get("timezone", parent.timezone),
        offset=calibration.get("offset", parent.offset),
        effects=data.get("effects", parent.effects),
        creator=data.get("creator", parent.creator),
    )
```

```python
# src/mkmapdiary/lib/asset.py — append to AssetRecord, after `effects` (line 48)
    creator: str | None = None
```

- [ ] **Step 4: Point taskList at resolve()**

Replace `taskList.py:222-233` (from `timezone = data.get(...)` through the `logger.debug` call) with:

```python
        calibration = resolve(data, self.__calibration[-1])
        self.__calibration.append(calibration)
        logger.debug(
            f"Applied calibration from {calibration_file}: "
            f"timezone={calibration.timezone}, offset={calibration.offset}, "
            f"creator={calibration.creator}",
            extra={"icon": "🛠️"},
        )
```

Update the import at `taskList.py:14` area to `from mkmapdiary.lib.calibration import Calibration, resolve`.

- [ ] **Step 5: Extend the calibration schema**

In `src/mkmapdiary/resources/calibrate_schema.yaml`, add after the `effects` block:

```yaml
  creator:
    type: ["string", "null"]
    description: >
      Name of the person who created the media in this directory. Inherited by
      subdirectories unless overridden. Set to null to clear an inherited creator.
    examples:
      - "Bob Ross"
```

and extend `anyOf`:

```yaml
anyOf:
  - required: ["calibration"]
  - required: ["effects"]
  - required: ["creator"]
```

The `anyOf` branch is **mandatory**: `write_calibration_data` (`commands/calibrate.py:138`) validates the *partial* dict before merging, so without it a creator-only write raises `ValidationError`.

- [ ] **Step 6: Run tests to verify they pass**

Run: `hatch test tests/test_creator_calibration.py tests/test_calibrate.py -v`
Expected: PASS.

- [ ] **Step 7: Full gate**

Run: `hatch run types:check && hatch run ruff:ruff check . && hatch test`
Expected: all pass.

- [ ] **Step 8: Commit**

```bash
git add src/mkmapdiary/lib/calibration.py src/mkmapdiary/lib/asset.py \
        src/mkmapdiary/resources/calibrate_schema.yaml src/mkmapdiary/taskList.py \
        tests/test_creator_calibration.py
git commit -m "feat: add a creator to the calibration stack"
```

---

### Task 2: EXIF artist extraction

**Files:**
- Modify: `src/mkmapdiary/tasks/base/exifReader.py`
- Test: `tests/test_creator_exif.py`

**Interfaces:**
- Consumes: nothing from Task 1.
- Produces: `ExifData.artist: str | None`; module-level `artist_from_exif(exif: dict[str, Any]) -> str | None` in `mkmapdiary.tasks.base.exifReader`.

Extract the tag logic as a module-level pure function so it is testable without the exiftool binary.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_creator_exif.py
from mkmapdiary.tasks.base.exifReader import ExifData, artist_from_exif


def test_reads_the_exif_artist_tag() -> None:
    assert artist_from_exif({"EXIF:Artist": "Bob Ross"}) == "Bob Ross"


def test_falls_back_to_iptc_byline() -> None:
    assert artist_from_exif({"IPTC:By-line": "Bob Ross"}) == "Bob Ross"


def test_falls_back_to_xmp_creator() -> None:
    assert artist_from_exif({"XMP:Creator": "Bob Ross"}) == "Bob Ross"


def test_exif_artist_wins_over_the_others() -> None:
    exif = {
        "EXIF:Artist": "Bob",
        "IPTC:By-line": "Janna",
        "XMP:Creator": "Alex",
    }
    assert artist_from_exif(exif) == "Bob"


def test_absent_tags_give_none() -> None:
    assert artist_from_exif({}) is None
    assert artist_from_exif({"EXIF:Make": "Canon"}) is None


def test_blank_tags_count_as_absent() -> None:
    """Cameras write an empty Artist field when the setting was never used."""
    assert artist_from_exif({"EXIF:Artist": ""}) is None
    assert artist_from_exif({"EXIF:Artist": "   "}) is None


def test_a_blank_tag_does_not_block_a_later_one() -> None:
    assert artist_from_exif({"EXIF:Artist": "  ", "IPTC:By-line": "Janna"}) == "Janna"


def test_values_are_stripped() -> None:
    assert artist_from_exif({"EXIF:Artist": "  Bob Ross \n"}) == "Bob Ross"


def test_non_string_values_are_ignored() -> None:
    """exiftool returns numbers for some tags; never crash on one."""
    assert artist_from_exif({"EXIF:Artist": 0}) is None


def test_exifdata_defaults_artist_to_none() -> None:
    assert ExifData().artist is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `hatch test tests/test_creator_exif.py -v`
Expected: FAIL with `ImportError: cannot import name 'artist_from_exif'`.

- [ ] **Step 3: Implement**

In `src/mkmapdiary/tasks/base/exifReader.py`, add `artist: str | None = None` to `ExifData` (after `orientation`, line 20), and add this module-level function after the `ExifData` class:

```python
ARTIST_TAGS = ("EXIF:Artist", "IPTC:By-line", "XMP:Creator")


def artist_from_exif(exif: dict[str, Any]) -> str | None:
    """The first non-blank authorship tag, or None.

    A camera that was never configured writes an empty Artist field, so a
    blank value must not shadow a populated tag further down the list.
    """
    for tag in ARTIST_TAGS:
        value = exif.get(tag)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None
```

Add `from typing import Any` to the imports.

In `read_exif`, after the existing `if not exif_data_dict:` guard block (line 50-53) and before the `date_formats` list, add:

```python
        exif_data.artist = artist_from_exif(exif_data_dict)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `hatch test tests/test_creator_exif.py -v`
Expected: PASS.

- [ ] **Step 5: Full gate**

Run: `hatch run types:check && hatch run ruff:ruff check . && hatch test`
Expected: all pass.

- [ ] **Step 6: Commit**

```bash
git add src/mkmapdiary/tasks/base/exifReader.py tests/test_creator_exif.py
git commit -m "feat: read the authorship tag from EXIF metadata"
```

---

### Task 3: Propagate the creator to assets

**Files:**
- Modify: `src/mkmapdiary/tasks/imageTask.py:34`
- Modify: `src/mkmapdiary/tasks/markdownTask.py:26`
- Modify: `src/mkmapdiary/tasks/textTask.py:26`
- Modify: `src/mkmapdiary/tasks/audioTask.py:42,49`
- Modify: `src/mkmapdiary/tasks/rawInputTask.py:49`
- Test: none — see below.

**Interfaces:**
- Consumes: `Calibration.creator` and `AssetRecord.creator` (Task 1); `ExifData.artist` (Task 2).
- Produces: every `AssetRecord` from these five handlers carries a resolved creator.

Precedence is `calibration.creator or exif_data.artist` — a deliberate `calibration.yaml` must beat a stale camera tag naming a previous owner.

**No new tests, by Janna's explicit decision.** The handlers build their
`AssetRecord`s inside a scan that needs a full `TaskList`, and the cheap
alternative — asserting on a bare Python `or` expression — would be a test
that verifies nothing. Verification here is the Step 2 grep; the creator's
behaviour on assets is covered by Task 5's registry tests. Do not add
tautological tests to fill the gap, and do not treat the absence as an
oversight to correct.

- [ ] **Step 1: Edit the five handlers**

`imageTask.py` — inside the `AssetRecord(...)` call, after `effects=calibration.effects.copy(),`:

```python
            creator=calibration.creator or exif_data.artist,
```

`markdownTask.py` and `textTask.py` — after `effects=calibration.effects.copy(),`:

```python
            creator=calibration.creator,
```

`audioTask.py` — the same line in **both** `AssetRecord(...)` calls (the `audio` asset and the `transcript` asset).

`rawInputTask.py` — after line 49 (`asset.effects = calibration.effects.copy()`):

```python
        asset.creator = calibration.creator or exif.artist
```

- [ ] **Step 2: Verify every handler was covered**

Run: `grep -n "creator" src/mkmapdiary/tasks/*Task.py`
Expected: six `creator=` / `asset.creator` lines — image (1), markdown (1), text (1), audio (2), rawInput (1). GPX is intentionally absent; it is Task 4.

- [ ] **Step 3: Full gate**

Run: `hatch run types:check && hatch run ruff:ruff check . && hatch test`
Expected: all pass.

- [ ] **Step 4: Commit**

```bash
git add src/mkmapdiary/tasks/imageTask.py src/mkmapdiary/tasks/markdownTask.py \
        src/mkmapdiary/tasks/textTask.py src/mkmapdiary/tasks/audioTask.py \
        src/mkmapdiary/tasks/rawInputTask.py
git commit -m "feat: carry the creator from calibration onto every asset"
```

---

### Task 4: GPX track creators

**Files:**
- Modify: `src/mkmapdiary/tasks/gpxTask.py:29-42`
- Test: `tests/test_creator_registry.py`

**Budget:** this task is ~6 lines of production code. If it grows beyond
that — if it starts needing changes in `GpxCreator`, per-date source
attribution, or more than the one property below — **stop and skip the task
entirely**, per Janna's instruction. Tracks going uncredited is an acceptable
outcome; a disproportionate GPX detour is not. If skipped, drop
`self.track_creators` from the `merge_creators(...)` call in Task 7 Step 6 and
pass `set()` in its place, and remove Task 7's abstract `track_creators`
property.

**Interfaces:**
- Consumes: `Calibration.creator` (Task 1).
- Produces: `GPXTask.track_creators -> set[str]` — a property, mirroring the existing `track_statistics` property at `gpxTask.py:31`. Task 7 unions it into the credits page.

Read the Spec Corrections section above before starting. The merged per-date GPX asset gets **no** creator: it can combine sources from directories with different creators, and there is no `Calibration` in scope where it is built. Instead `handle_gpx` — which *does* have the calibration — records the creator of each source file, and that set feeds the credits page only. Tracks have no metadata line, so nothing is lost.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_creator_registry.py
from mkmapdiary.tasks.gpxTask import GPXTask


class _StubGPXTask(GPXTask):
    """GPXTask without the BaseTask machinery a real scan would need."""

    def __init__(self) -> None:
        super().__init__()


def test_track_creators_starts_empty() -> None:
    assert _StubGPXTask().track_creators == set()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `hatch test tests/test_creator_registry.py -v`
Expected: FAIL with `AttributeError: 'GPXTask' object has no attribute 'track_creators'`.

If instantiating `_StubGPXTask` fails on abstract methods, drop the stub and assert on the class instead: `assert isinstance(GPXTask.track_creators, property)`. Do not weaken the test further than that — note the reason in the test docstring.

- [ ] **Step 3: Implement**

In `gpxTask.py.__init__` (line 27-29), add beside `self.__sources`:

```python
        self.__source_creators: set[str] = set()
```

Add the property next to `track_statistics`:

```python
    @property
    def track_creators(self) -> set[str]:
        """Creators of the GPX *source* files.

        The generated per-date GPX merges several sources and so has no single
        creator; this set feeds the credits page instead. See the plan's Spec
        Corrections section.
        """
        return set(self.__source_creators)
```

In `handle_gpx` (line 35), after `self.__sources.append(source)`:

```python
        if calibration.creator is not None:
            self.__source_creators.add(calibration.creator)
```

Do **not** add an abstract `track_creators` to `GalleryTask`. It declares an
abstract `track_statistics` because it *uses* it (`galleryTask.py:97`);
`track_creators` is consumed only by `SiteTask`, which declares it in Task 7.

- [ ] **Step 4: Run tests to verify they pass**

Run: `hatch test tests/test_creator_registry.py -v`
Expected: PASS.

- [ ] **Step 5: Full gate**

Run: `hatch run types:check && hatch run ruff:ruff check . && hatch test`
Expected: all pass. Watch for mypy complaining that `TaskList` no longer satisfies an abstract property — if so, confirm `GPXTask` is in the `tasks` list in `taskList.py`.

- [ ] **Step 6: Commit**

```bash
git add src/mkmapdiary/tasks/gpxTask.py tests/test_creator_registry.py
git commit -m "feat: collect creators from GPX source files"
```

---

### Task 5: Conditional per-asset display

**Files:**
- Modify: `src/mkmapdiary/lib/assetRegistry.py`
- Modify: `src/mkmapdiary/tasks/base/baseTask.py`
- Modify: `src/mkmapdiary/tasks/journalTask.py:60-70,74-79`
- Modify: `src/mkmapdiary/tasks/galleryTask.py:100-116`
- Modify: `src/mkmapdiary/tasks/siteTask.py:253-264`
- Modify: `src/mkmapdiary/templates/day_journal.j2`, `day_gallery.j2`, `index.j2`
- Test: `tests/test_creator_registry.py` (extend), `tests/test_creator_templates.py`

**Interfaces:**
- Consumes: `AssetRecord.creator` (Task 1, populated by Task 3).
- Produces: `AssetRegistry.distinct_creators() -> set[str | None]`; `BaseTask.show_creators -> bool`; template variable `show_creators` on all three templates.

The rule: show a creator per-asset **iff the journal holds at least two distinct creator values, counting `None` as a value**. One uniform creator is suppressed because repeating one name on every photo carries no information. A mixed journal is *not* suppressed — "Bob shot this one, and we are not saying who shot the rest" is a real distinction.

- [ ] **Step 1: Write the failing registry test**

Append to `tests/test_creator_registry.py`:

```python
from pathlib import PosixPath

from mkmapdiary.lib.asset import AssetRecord
from mkmapdiary.lib.assetRegistry import AssetRegistry


def _registry(*creators: str | None) -> AssetRegistry:
    registry = AssetRegistry()
    for i, creator in enumerate(creators):
        registry.add_asset(
            AssetRecord(path=PosixPath(f"{i}.jpg"), type="image", creator=creator)
        )
    return registry


def test_distinct_creators_counts_none_as_a_value() -> None:
    assert _registry("Bob", None).distinct_creators() == {"Bob", None}


def test_distinct_creators_deduplicates() -> None:
    assert _registry("Bob", "Bob", "Bob").distinct_creators() == {"Bob"}


def test_empty_registry_has_no_creators() -> None:
    assert AssetRegistry().distinct_creators() == set()


def test_threshold_empty_journal() -> None:
    assert len(AssetRegistry().distinct_creators()) < 2


def test_threshold_uniform_single_creator_is_suppressed() -> None:
    assert len(_registry("Bob", "Bob").distinct_creators()) < 2


def test_threshold_all_unattributed_is_suppressed() -> None:
    assert len(_registry(None, None).distinct_creators()) < 2


def test_threshold_mixed_named_and_unattributed_is_shown() -> None:
    """Bob shot one directory and the rest is unattributed — a real distinction."""
    assert len(_registry("Bob", None).distinct_creators()) >= 2


def test_threshold_two_named_creators_is_shown() -> None:
    assert len(_registry("Bob", "Janna").distinct_creators()) >= 2
```

- [ ] **Step 2: Run test to verify it fails**

Run: `hatch test tests/test_creator_registry.py -v`
Expected: FAIL with `AttributeError: 'AssetRegistry' object has no attribute 'distinct_creators'`.

- [ ] **Step 3: Implement the registry method and the property**

In `assetRegistry.py`, after `get_all_assets` (line 86-92):

```python
    def distinct_creators(self) -> set[str | None]:
        """Every distinct creator value, with None kept as a value.

        None is significant: a journal mixing named and unattributed assets
        has two distinct values and so does show creators per asset.
        """
        with self.lock:
            return {asset.creator for asset in self.__assets}
```

Note `self.__assets` is name-mangled to `_AssetRegistry__assets` — the method must live inside the class, not be patched on.

In `baseTask.py`, after the abstract `db` property (line 68-71):

```python
    @property
    def show_creators(self) -> bool:
        """Whether to render a creator on each asset's metadata line.

        Suppressed unless the journal holds more than one distinct creator
        value; one name repeated on every photo carries no information.
        """
        return len(self.db.distinct_creators()) >= 2
```

- [ ] **Step 4: Run registry tests**

Run: `hatch test tests/test_creator_registry.py -v`
Expected: PASS.

- [ ] **Step 5: Write the failing template test**

```python
# tests/test_creator_templates.py
"""The creator line on the three templates that carry asset metadata."""

from typing import Any

from jinja2 import Environment, PackageLoader, StrictUndefined, select_autoescape

STRINGS: dict[str, Any] = {
    "journal_title": "Journal",
    "gallery_title": "Gallery",
    "map_title": "Map",
    "overview_title": "Overview",
    "zoom_to_fit": "Zoom to fit",
    "download_gpx": "Download GPX",
    "legend_track": "Track",
    "legend_waypoints": "Waypoints",
    "legend_activity_areas": "Activity areas",
    "legend_journal_entries": "Journal entries",
    "include_duplicates": "Include duplicates",
    "include_low_quality": "Include low quality",
    "show_quality_icons": "Show quality icons",
    "quality_good": "Good",
    "quality_bad": "Bad",
    "quality_excellent": "Excellent",
    "quality_low_entropy": "Low entropy",
    "quality_duplicate": "Duplicate",
    "quality_canonical": "Canonical",
    "track_label": "Track",
    "track_distance": "Distance",
    "track_elevation_gain": "Gain",
    "track_elevation_loss": "Loss",
    "track_time_moving": "Moving",
    "track_total_time": "Total",
}


def _env() -> Environment:
    return Environment(
        loader=PackageLoader("mkmapdiary"),
        autoescape=select_autoescape(),
        undefined=StrictUndefined,
    )


def _journal(**params: Any) -> str:
    asset: dict[str, Any] = {
        "id": 1,
        "type": "markdown",
        "path": "note.md",
        "time": "14:32",
        "timezone": "Europe/Paris",
        "latitude": None,
        "longitude": None,
        "location": None,
        "location_admin": None,
        "creator": "Bob",
    }
    asset.update(params.pop("asset", {}))
    defaults: dict[str, Any] = {
        "assets": [asset],
        "strings": STRINGS,
        "show_creators": True,
    }
    defaults.update(params)
    return _env().get_template("day_journal.j2").render(**defaults)


def test_journal_shows_the_creator_when_enabled() -> None:
    assert "Bob" in _journal()


def test_journal_hides_the_creator_when_disabled() -> None:
    """A journal with one uniform creator repeats a name that says nothing."""
    assert "Bob" not in _journal(show_creators=False)


def test_journal_renders_no_separator_for_an_unattributed_asset() -> None:
    """show_creators is journal-wide; individual assets may still have none."""
    output = _journal(asset={"creator": None})

    assert "iconoir-user" not in output


def test_journal_carries_no_ai_label() -> None:
    """Creator attribution is human authorship, not machine-generated output."""
    assert "ai-generated" not in _journal()
```

Add equivalent `_gallery()` and `_index()` helpers rendering `day_gallery.j2` and `index.j2`. Read those two templates first to collect the full variable list `StrictUndefined` demands (`gallery_items`, `geo_items`, `gpx_data`, `gpx_file`, `track_statistics`, `highlight_images`, `has_bad_photos`, `has_duplicates`, and for `index.j2` whatever `siteTask.py:255-263` passes). Each gets the same four assertions.

- [ ] **Step 6: Run template test to verify it fails**

Run: `hatch test tests/test_creator_templates.py -v`
Expected: FAIL — `"Bob" in output` is False, because no template renders a creator yet.

- [ ] **Step 7: Edit the three templates**

`day_journal.j2` — after the `location_admin` line (line 15), inside the `<div class="metadata">`:

```jinja
{% if show_creators and asset.creator %}· <i class="iconoir iconoir-user"></i> {{ asset.creator }}{% endif %}
```

`day_gallery.j2` — after line 84, inside `<div class="glightbox-desc ...">`, matching that block's whitespace-control style:

```jinja
{%- if show_creators and item.creator %} · <i class="iconoir iconoir-user"></i> {{ item.creator }}{% endif %}
```

`index.j2` — the same line as `day_gallery.j2`, after line 14.

- [ ] **Step 8: Pass show_creators from all three render sites**

`journalTask.py` — add `creator=asset_data.creator,` to the `item = dict(...)` at line 60-70. This dict is built **field by field**, so unlike the other two it does not get the field for free. Then add `show_creators=self.show_creators,` to the `self.template("day_journal.j2", ...)` call at line 74-79.

`galleryTask.py` — add `show_creators=self.show_creators,` to the `self.template("day_gallery.j2", ...)` call at line 100-116. The dicts already come from `dataclasses.asdict`, so `creator` is present.

`siteTask.py` — add `show_creators=self.show_creators,` to the `self.template("index.j2", ...)` call at line 254-263. Same `asdict` note.

- [ ] **Step 9: Run tests to verify they pass**

Run: `hatch test tests/test_creator_templates.py tests/test_creator_registry.py -v`
Expected: PASS.

- [ ] **Step 10: Full gate**

Run: `hatch run types:check && hatch run ruff:ruff check . && hatch test`
Expected: all pass.

- [ ] **Step 11: Commit**

```bash
git add src/mkmapdiary/lib/assetRegistry.py src/mkmapdiary/tasks/base/baseTask.py \
        src/mkmapdiary/tasks/journalTask.py src/mkmapdiary/tasks/galleryTask.py \
        src/mkmapdiary/tasks/siteTask.py src/mkmapdiary/templates/day_journal.j2 \
        src/mkmapdiary/templates/day_gallery.j2 src/mkmapdiary/templates/index.j2 \
        tests/test_creator_registry.py tests/test_creator_templates.py
git commit -m "feat: show the creator on assets when the journal has several"
```

---

### Task 6: `mkmapdiary calibrate creator`

**Files:**
- Modify: `src/mkmapdiary/commands/calibrate.py`
- Test: `tests/test_creator_command.py`

**Interfaces:**
- Consumes: the `creator` schema key and its `anyOf` branch (Task 1).
- Produces: the `creator` click command, registered on the `calibrate` group.

Mirrors the existing `effects` subcommand (line 201-266), including its required `-o/--output` that accepts a directory or a file, and `-n/--dry-run`. `write_calibration_data` merges into any existing file, so `calibration` and `effects` keys survive.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_creator_command.py
from pathlib import Path

import yaml
from click.testing import CliRunner

from mkmapdiary.commands.calibrate import calibrate


def _run(*args: str) -> Any:
    return CliRunner().invoke(calibrate, ["creator", *args])


def test_writes_a_creator_into_a_new_file(tmp_path: Path) -> None:
    result = _run("-o", str(tmp_path), "Bob Ross")

    assert result.exit_code == 0
    written = yaml.safe_load((tmp_path / "calibration.yaml").read_text())
    assert written["creator"] == "Bob Ross"


def test_preserves_existing_calibration_keys(tmp_path: Path) -> None:
    """The merge in write_calibration_data must not drop timezone/offset."""
    target = tmp_path / "calibration.yaml"
    target.write_text(
        yaml.safe_dump(
            {"calibration": {"timezone": "UTC", "offset": 42}, "effects": ["autorotate"]}
        )
    )

    assert _run("-o", str(target), "Bob Ross").exit_code == 0

    written = yaml.safe_load(target.read_text())
    assert written["creator"] == "Bob Ross"
    assert written["calibration"] == {"timezone": "UTC", "offset": 42}
    assert written["effects"] == ["autorotate"]


def test_unset_writes_an_explicit_null(tmp_path: Path) -> None:
    """Null clears an inherited creator; omitting the key would inherit it."""
    assert _run("-o", str(tmp_path), "--unset").exit_code == 0

    written = yaml.safe_load((tmp_path / "calibration.yaml").read_text())
    assert "creator" in written
    assert written["creator"] is None


def test_name_and_unset_together_is_an_error(tmp_path: Path) -> None:
    result = _run("-o", str(tmp_path), "--unset", "Bob Ross")

    assert result.exit_code != 0
    assert not (tmp_path / "calibration.yaml").exists()


def test_neither_name_nor_unset_is_an_error(tmp_path: Path) -> None:
    result = _run("-o", str(tmp_path))

    assert result.exit_code != 0
    assert not (tmp_path / "calibration.yaml").exists()


def test_dry_run_writes_nothing(tmp_path: Path) -> None:
    assert _run("-o", str(tmp_path), "-n", "Bob Ross").exit_code == 0
    assert not (tmp_path / "calibration.yaml").exists()
```

Add `from typing import Any` at the top.

- [ ] **Step 2: Run test to verify it fails**

Run: `hatch test tests/test_creator_command.py -v`
Expected: FAIL — `No such command 'creator'`.

- [ ] **Step 3: Implement**

Add to `commands/calibrate.py`, after the `effects` command:

```python
@click.command()
@click.option("-o", "--output", type=click.Path(path_type=Path), required=True)
@click.option(
    "--unset",
    is_flag=True,
    help="Clear the creator for this directory instead of setting one. "
    "Writes an explicit null, which overrides an inherited creator; "
    "omitting the key entirely would inherit it instead.",
)
@click.option(
    "-n", "--dry-run", is_flag=True, help="Perform a dry run without writing output."
)
@click.argument("name", type=str, required=False)
def creator(output: Path, unset: bool, dry_run: bool, name: str | None) -> None:
    """Set the creator of the media in a directory."""

    if unset and name is not None:
        raise click.UsageError("Give either a name or --unset, not both.")
    if not unset and name is None:
        raise click.UsageError("Give a name, or --unset to clear the creator.")

    if output.is_dir():
        output = output / "calibration.yaml"

    write_calibration_data({"creator": None if unset else name}, output, dry_run)
```

Register it on the group alongside the existing commands — find the `calibrate.add_command(effects)` line (or equivalent) and add `calibrate.add_command(creator)`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `hatch test tests/test_creator_command.py -v`
Expected: PASS. A failure mentioning `ValidationError` means the `anyOf` branch from Task 1 Step 5 is missing.

- [ ] **Step 5: Full gate**

Run: `hatch run types:check && hatch run ruff:ruff check . && hatch test`
Expected: all pass.

- [ ] **Step 6: Commit**

```bash
git add src/mkmapdiary/commands/calibrate.py tests/test_creator_command.py
git commit -m "feat: add a calibrate creator subcommand"
```

---

### Task 7: Credits page section

**Files:**
- Modify: `src/mkmapdiary/resources/defaults.yaml:88-90,125-135`
- Modify: `src/mkmapdiary/resources/config_schema.yaml:236-245,321-347`
- Modify: `src/mkmapdiary/locale/{de,en}/LC_MESSAGES/messages.po:435`
- Modify: `src/mkmapdiary/tasks/siteTask.py:33,364-400`
- Modify: `src/mkmapdiary/templates/credits.j2:9`
- Modify: `docs/reference/configuration.md`, `CLAUDE.md`
- Test: `tests/test_credits_template.py` (extend), `tests/test_creator_registry.py` (extend)

**Interfaces:**
- Consumes: `AssetRegistry.distinct_creators()` (Task 5); `GPXTask.track_creators` (Task 4).
- Produces: `mkmapdiary.tasks.siteTask.merge_creators(config_creators, asset_creators, track_creators) -> list[str]`; template variable `creators` on `credits.j2`.

- [ ] **Step 1: Write the failing merge test**

Append to `tests/test_creator_registry.py`:

```python
from mkmapdiary.tasks.siteTask import merge_creators


def test_merge_unions_all_three_sources() -> None:
    assert merge_creators(["Chris"], {"Bob"}, {"Alex"}) == ["Alex", "Bob", "Chris"]


def test_merge_deduplicates_across_sources() -> None:
    assert merge_creators(["Janna"], {"Janna", "Bob"}, {"Janna"}) == ["Bob", "Janna"]


def test_merge_drops_the_none_placeholder() -> None:
    """distinct_creators keeps None as a value; the credits page must not."""
    assert merge_creators([], {"Bob", None}, set()) == ["Bob"]


def test_merge_of_nothing_is_empty() -> None:
    assert merge_creators([], set(), set()) == []
```

- [ ] **Step 2: Write the failing template test**

Append to `tests/test_credits_template.py`, and add `"credits_creators": "Creators"` to that file's `STRINGS` dict and `"creators": []` to its `defaults` dict in `_render`:

```python
def test_renders_creators() -> None:
    output = _render(creators=["Bob Ross", "Janna Hopp"])

    assert "Creators" in output
    assert "Bob Ross" in output
    assert "Janna Hopp" in output


def test_omits_the_creators_section_when_empty() -> None:
    assert "Creators" not in _render(creators=[])


def test_creators_are_separate_from_travellers() -> None:
    """Who travelled and who authored are different claims."""
    output = _render(travellers=["Alex"], creators=["Bob"])

    assert "Travellers" in output
    assert "Creators" in output
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `hatch test tests/test_creator_registry.py tests/test_credits_template.py -v`
Expected: FAIL — `ImportError: cannot import name 'merge_creators'`, and the credits assertions fail.

- [ ] **Step 4: Add the config key**

`defaults.yaml`, in the `credits` block (line 88-90):

```yaml
credits:
  # Names of the people who travelled; shown on the generated credits page
  travellers: []
  # General credit for the media; merged with the creators found in
  # calibration.yaml files. Does not appear on individual assets.
  creators: []
```

`defaults.yaml`, in the `strings` block after `credits_travellers: null`:

```yaml
  credits_creators: null
```

`config_schema.yaml`, in the `credits` properties block (line 240-244) — this block is `additionalProperties: false`, so the key must be listed:

```yaml
      creators:
        type: array
        description: "General credit for the media, merged with calibration creators"
        items:
          type: string
```

`config_schema.yaml`, in the `strings` properties after `credits_travellers` (line 323-324):

```yaml
      credits_creators:
        $ref: "#/definitions/customString"
```

- [ ] **Step 5: Add the translations**

`locale/en/LC_MESSAGES/messages.po`, after the `credits_travellers` entry:

```
msgid "credits_creators"
msgstr "Creators"
```

`locale/de/LC_MESSAGES/messages.po`, same position:

```
msgid "credits_creators"
msgstr "Urheber*innen"
```

Then run `task translate`. Pre-commit fails on stale `.mo` files otherwise.

- [ ] **Step 6: Implement merge_creators and wire the task**

In `siteTask.py`, as a module-level function beside the existing `credits_libraries` (line 33):

```python
def merge_creators(
    config_creators: list[str],
    asset_creators: set[str | None],
    track_creators: set[str],
) -> list[str]:
    """One deduplicated, sorted credit list from all three sources.

    `asset_creators` keeps None as a value so the display threshold can count
    it; the credits page drops it, since "nobody" is not a name.
    """
    merged = set(config_creators) | asset_creators | track_creators
    return sorted(name for name in merged if name is not None)
```

Add the abstract property to `SiteTask` (it needs `track_creators` from `GPXTask`), beside its other abstract declarations:

```python
    @property
    @abstractmethod
    def track_creators(self) -> set[str]:
        raise NotImplementedError("SiteTask does not provide track creators.")
```

In `task_build_credits_page`'s `self.template("credits.j2", ...)` call (line 385-391), add:

```python
                creators=merge_creators(
                    self.config["credits"]["creators"],
                    self.db.distinct_creators(),
                    self.track_creators,
                ),
```

That task already carries `uptodate=[False]` (line 400), so a config-only change to `creators` still rebuilds the page. Do not remove it.

- [ ] **Step 7: Edit the credits template**

In `credits.j2`, replace line 9 — `{# Photographers belong here once that feature lands. #}` — with:

```jinja
{% if creators %}
## {{ strings.credits_creators }}

{{ creators | join(", ") }}

{% endif %}
```

- [ ] **Step 8: Run tests to verify they pass**

Run: `hatch test tests/test_creator_registry.py tests/test_credits_template.py tests/test_credits_config.py -v`
Expected: PASS. `test_credits_config.py` may assert on the shape of the `credits` config block — if it fails, extend it for the new key rather than working around it.

- [ ] **Step 9: Document**

In `docs/reference/configuration.md`, beside `credits.travellers`, document `credits.creators`: a general credit for the media, merged and deduplicated with the creators picked up from `calibration.yaml` files and from EXIF, shown only on the credits page and never on an individual asset.

In `CLAUDE.md`, in the i18n bullet of "Cross-cutting concerns", add:

```markdown
  **Gender-neutral German**: prefer neutral formulations — substantivierte
  Partizipien (`Reisende`), abstract nouns, or reformulation. Where a gendered
  noun is unavoidable, use the asterisk (`Urheber*innen`), not the colon or
  Binnen-I. Precision that still reads as normal German wins: `Urheberschaft`
  is legalese nobody says, and `Mitwirkende` is so broad it collapses into
  `Reisende`, the section right next to it.
```

- [ ] **Step 10: Full gate**

Run: `task test`
Expected: all pass, including the translation-freshness check.

- [ ] **Step 11: Commit**

```bash
git add src/mkmapdiary/resources/defaults.yaml src/mkmapdiary/resources/config_schema.yaml \
        src/mkmapdiary/locale/de/LC_MESSAGES/messages.po src/mkmapdiary/locale/de/LC_MESSAGES/messages.mo \
        src/mkmapdiary/locale/en/LC_MESSAGES/messages.po src/mkmapdiary/locale/en/LC_MESSAGES/messages.mo \
        src/mkmapdiary/tasks/siteTask.py src/mkmapdiary/templates/credits.j2 \
        docs/reference/configuration.md CLAUDE.md \
        tests/test_creator_registry.py tests/test_credits_template.py
git commit -m "feat: credit the creators of the media on the credits page"
```

---

### Task 8: Three layout defects

**Files:**
- Modify: `src/mkmapdiary/templates/index.j2`
- Modify: `src/mkmapdiary/resources/extra.sass`
- Modify: `src/mkmapdiary/resources/gallery.js`

**Interfaces:**
- Consumes: nothing. Independent of Tasks 1-7 and safe to do in any order.
- Produces: nothing other tasks rely on.

Three defects Janna reported, grouped because they share one verification
loop: a single build session covers all three. **8a is confirmed statically
and can be fixed now. 8b and 8c are hypotheses and must be diagnosed against
a real build before anything is edited.**

Only 8c is caused by this feature's work; 8a and 8b are pre-existing. All
three ship together because the creator field makes 8c routine rather than
rare, and because they are the same kind of fix in the same files.

#### 8a — Stray `</div>` in `index.j2` (confirmed)

`index.j2` contains six `<div` and seven `</div>`. The imbalance is at line 8:

```jinja
</div>                                      {# line 7: closes #highlights #}
</div><div id="gallery_captions" markdown>  {# line 8: this </div> closes nothing #}
```

Line 8 was copied from `day_gallery.j2`, where the leading `</div>` correctly
closes `#photo_gallery`. `index.j2` has no such div open, so the tag closes an
ancestor — the theme's content wrapper — putting everything after it outside
the container. `day_gallery.j2` is balanced (7/7) and must not be touched.

- [ ] **Step 1: Delete the stray tag**

Remove the leading `</div>` from line 8 of `index.j2` so it reads:

```jinja
<div id="gallery_captions" markdown>
```

- [ ] **Step 2: Verify balance**

Run: `grep -c "<div" src/mkmapdiary/templates/index.j2 && grep -c "</div>" src/mkmapdiary/templates/index.j2`
Expected: `6` and `6`.

- [ ] **Step 3: Commit**

```bash
git add src/mkmapdiary/templates/index.j2
git commit -m "fix: remove a stray closing div from the start page"
```

#### 8b — Gap below the highlights — RESOLVED BY 8a, NO SEPARATE FIX

**Outcome: fixed by 8a; the hypothesis below was never confirmed and is
almost certainly wrong.** Janna verified the gap was gone after the stray
`</div>` was removed. That fits: the unbalanced tag closed an ancestor
element early, so the floated highlights were no longer contained by the
wrapper meant to hold them, and `.clear` could not clear them against it.

A div-balance check across all nine templates afterwards shows every one
balanced, so no sibling defect remains. **Do not implement the justifiedGallery
fix described below.** It is retained only as a record of a hypothesis that
the evidence did not support — a reminder that "the gap is exactly one image
row" pointed at float containment, not at the layout plugin.

---

<details>
<summary>Original (unconfirmed, superseded) hypothesis</summary>

A gap roughly one image-row tall sits between the highlights strip and the
map, on the start page and on day pages.

**Hypothesis:** the highlights are laid out by justifiedGallery
(`gallery.js:28-29`) with `maxRowsCount: window.highlight_max_rows` and
`lastRow: 'hide'` (`gallery.js:13-14`). That plugin sets an explicit pixel
height on its container; the row it hides is still counted in that height, so
the container reserves space for images it does not draw. Janna's measurement
— the gap is exactly an image row — fits this.

This is a hypothesis. Confirm it in the browser before editing.

- [ ] **Step 1: Confirm against a real build**

Ask Janna for a build. Inspect the `#highlights p` element: read its computed
`height` and compare with the height its visible rows actually occupy. A
container taller than its visible rows confirms the hypothesis.

- [ ] **Step 2: Fix at the confirmed cause**

If confirmed, correct the container height after layout completes — hook
justifiedGallery's `jg.complete` event and reset the height to the visible
rows. Prefer the plugin's own API over a CSS override that fights it.

If the cause turns out to be something else, follow the evidence and say so
in the commit message. Do not implement the fix above unless Step 1 confirmed
it.

- [ ] **Step 3: Verify and commit**

Ask Janna to rebuild and confirm the gap is gone on both the start page and a
day page, and that highlights still lay out correctly at several window
widths.

```bash
git add src/mkmapdiary/resources/gallery.js
git commit -m "fix: stop the highlights reserving space for a hidden row"
```

</details>

#### 8c — Wrapped captions clip (hypothesis)

The asset metadata line clips its second line when it wraps, shearing text
mid-glyph — observed in the lightbox caption, where a trailing `Frankreich`
was cut. Adding a creator makes that line wrap in the common case.

`extra.sass:273` contains only `#gallery_captions { display: none }`; the
visible caption box is styled by **mkdocs-glightbox's own CSS**. The
hypothesis is a fixed height or `overflow: hidden` on the description
element, sized upstream for a single line. That is a hypothesis, not a
finding.

- [ ] **Step 1: Diagnose against a real build**

From the built site, identify the actual element and the actual property
doing the clipping — inspect the generated CSS for the description container
(`.gslide-description`, `.gdesc-inner`, or whatever the installed
mkdocs-glightbox version emits). Record the real selector and declaration.

Do not guess selector names from this plan.

- [ ] **Step 2: Write the override**

Add a targeted rule to `extra.sass` next to the existing `#gallery_captions`
block, in the file's indentation-based Sass syntax (no braces). Scope it to
the caption container only — do not restyle the lightbox generally.

- [ ] **Step 3: Verify and commit**

Ask Janna to rebuild and confirm a wrapped caption shows both lines in full
and a single-line caption is unchanged.

```bash
git add src/mkmapdiary/resources/extra.sass
git commit -m "fix: stop wrapped asset captions clipping their second line"
```

#### Whole-task gate

- [ ] **Final step: Full gate**

Run: `task test`
Expected: all pass.

**Builds:** do **not** run `task example` — the project rule reserves it for
Janna. `task demo` is permitted and may reproduce all three with placeholder
data; try it before asking.

---

### Task 9: Amend the spec

**Files:**
- Modify: `docs/superpowers/specs/2026-08-02-creator-credits-design.md`

**Interfaces:**
- Consumes: the corrections established in Tasks 4 and 5.
- Produces: nothing.

The spec, as committed in `9b5c0a6`, states three things the code contradicted. Leaving it wrong strands the next reader.

- [ ] **Step 1: Correct the GPX section**

Replace the claim that `gpxTask.py:132` gains `creator=calibration.creator` with the `track_creators` design from Task 4, including why the merged per-date asset cannot carry one.

- [ ] **Step 2: Correct the template count**

Change "both templates" / "two templates" to three, naming `index.j2:10-14` alongside `day_journal.j2` and `day_gallery.j2`.

- [ ] **Step 3: Correct the asdict claim**

Note that `journalTask.py:60-70` builds its item dict field by field and needs `creator` added explicitly; only `galleryTask` and `siteTask` get it free from `dataclasses.asdict`.

- [ ] **Step 4: Commit**

```bash
git add docs/superpowers/specs/2026-08-02-creator-credits-design.md
git commit -m "docs: correct the creator credits spec against the code"
```

---

## Verification

Run the full gate exactly as pre-commit does:

```bash
task test
```

Then confirm by hand:

- `grep -rn "creator" src/mkmapdiary/templates/` shows the line on exactly three templates plus the credits section.
- `grep -rn "show_creators" src/mkmapdiary/tasks/` shows three render sites plus the `BaseTask` property.
- `hatch run mkmapdiary calibrate creator --help` prints the new command.
- `hatch run mkmapdiary config` (or the schema validation path) accepts a config carrying `credits.creators`.

The end-to-end behaviour — a real journal showing creators on assets and on the credits page — needs a build with multi-directory sources. Ask Janna; do not run the examples.
