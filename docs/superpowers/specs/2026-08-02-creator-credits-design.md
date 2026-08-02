# Creator credits

Attribute media in a journal to the people who made it: a per-directory
`creator` in the calibration stack, a general credit in the config, an
attribution on each asset's metadata line, and a combined section on the
credits page.

## Motivation

A journal built from several people's cameras currently credits nobody. The
credits page has carried the placeholder `{# Photographers belong here once
that feature lands. #}` (`credits.j2:9`) since the page was written.

Attribution is per-directory in practice — one card, one camera, one person —
which is exactly the granularity the calibration stack already provides.

## Data model

`Calibration` (`lib/calibration.py`) gains a fourth field, and `AssetRecord`
(`lib/asset.py`) a matching one:

```python
class Calibration(NamedTuple):
    timezone: str
    offset: int
    effects: list[str] = []
    creator: str | None = None
```

`AssetMetadata` is deliberately **not** used. `imageSummarizer.py:33` and
`journalSummarizer.py:29` replace that entire object with LLM output, so a
human name stored there would be destroyed on the next build and would sit
inside an AI-generated structure — which the AI-transparency rule in
`CLAUDE.md` reserves for machine-generated content.

### Resolution order

```
calibration.yaml (directory stack)   →  AssetRecord.creator
        ↓ if none
EXIF:Artist / IPTC:By-line / XMP:Creator   (images and RAW only)
        ↓ if none
None
```

Config `credits.creators` is **not** a per-asset fallback. It is a page-level
general credit only, and never renders on an asset's metadata line.

## Calibration schema

`resources/calibrate_schema.yaml` gains a root-level `creator` — a sibling of
`effects`, not a member of the `calibration` block, because that block requires
`timezone` and `offset` together and a creator-only file must validate:

```yaml
  creator:
    type: ["string", "null"]
    description: >
      Name of the person who created the media in this directory.
      Inherited by subdirectories. Set to null to clear an inherited creator.
```

`anyOf` gains `- required: ["creator"]`. This is **mandatory, not cosmetic**:
`write_calibration_data` (`commands/calibrate.py:133`) validates the *partial*
dict it is handed before merging it into the existing file, so without the new
`anyOf` branch a creator-only write fails validation.

### Inheritance

`__push_calibration` (`taskList.py:212`) resolves it exactly as it resolves
`effects`:

```python
creator = data.get("creator", self.__calibration[-1].creator)
```

A subdirectory inherits its parent's creator unless it overrides. Writing
`creator: null` explicitly clears it for that subtree — distinct from omitting
the key, which inherits.

## Propagation to assets

Every handler that already copies `calibration.effects` gains
`creator=calibration.creator` beside it:

| File | Line | Note |
| --- | --- | --- |
| `tasks/imageTask.py` | 34 | plus EXIF fallback |
| `tasks/rawInputTask.py` | 49 | assignment form; plus EXIF fallback |
| `tasks/markdownTask.py` | 26 | |
| `tasks/audioTask.py` | 42, 49 | two records |
| `tasks/textTask.py` | 26 | |

GPX is different from the rest of this table and does not fit the pattern.
`handle_gpx` (`tasks/gpxTask.py`) yields no `AssetRecord` at all — at scan time
it is not yet knowable which dates a GPX file covers, so the handler only
records the source path for later processing. The one place a GPX
`AssetRecord` *is* built is inside the `_generate_all_gpx_files` action of
`task_gpx2gpx`, which runs after scanning, has no `Calibration` in scope, and
produces a single per-date file merged from every source that touches that
date. Sources from directories with different creators can land in the same
merged file, so there is no single creator to assign it — `creator=
calibration.creator` on that `AssetRecord` is not just missing, it has no
value to be.

Instead, `handle_gpx` collects each source file's `calibration.creator` into a
`set[str]`, exposed as the `track_creators` property. This feeds the credits
page only. Tracks have no metadata line, so nothing is lost by the merged file
carrying no creator of its own.

### EXIF fallback

`ExifData` (`tasks/base/exifReader.py:15`) gains `artist: str | None = None`.
`read_exif` reads the first present of `EXIF:Artist`, `IPTC:By-line`,
`XMP:Creator`, stripping whitespace and treating an empty result as absent.

The two image handlers resolve `calibration.creator or exif_data.artist`.
Calibration wins: a deliberate `calibration.yaml` must not be overridden by a
stale camera tag naming a previous owner. Audio, markdown, text and GPX never
consult EXIF.

## `mkmapdiary calibrate creator`

Mirrors the existing `calibrate effects` subcommand, including its
`-o/--output` (required, accepts a directory or a file path) and `-n/--dry-run`:

```bash
mkmapdiary calibrate creator -o ./photos/bobs-camera "Bob Ross"
mkmapdiary calibrate creator -o ./photos/borrowed --unset
```

`NAME` is a positional argument, required unless `--unset` is given; supplying
both is an error. The command builds `{"creator": name}` (or
`{"creator": None}`) and hands it to `write_calibration_data`, which merges it
into any existing `calibration.yaml`, preserving `calibration` and `effects`.

## Per-asset display

`creator` reaches templates two different ways. `siteTask.py:232` and
`galleryTask.py:45` build their per-asset dicts with `dataclasses.asdict(asset)`,
so `creator` arrives for free once it is a field on `AssetRecord`.
`journalTask.py:60-70` does not: it builds its item dict field by field, and
needs `creator=asset_data.creator` added explicitly alongside the other fields
it already assembles by hand.

### Visibility rule

A creator is shown per-asset **iff the journal contains at least two distinct
creator values, counting `None` as a value**:

```python
show_creators = len({a.creator for a in registry.get_all_assets()}) >= 2
```

| Journal | Shown |
| --- | --- |
| No creators anywhere | no |
| One creator, uniform across all assets | no |
| Bob on some assets, nothing on the rest | yes |
| Bob and Janna | yes |

The single-creator case is suppressed because repeating one name on every photo
carries no information; the credits page still names them. The mixed case is
*not* suppressed — "Bob shot this one, and we are not saying who shot the rest"
is a real distinction.

A new `AssetRegistry.distinct_creators() -> set[str | None]` computes the set;
all three page-building tasks derive the bool and pass `show_creators` into
their template call.

### Templates

All three metadata lines gain the same conditional, following the existing
`location_admin` pattern — `day_journal.j2` after line 15, `day_gallery.j2`
after line 84, and `index.j2:10-14`:

```jinja
{% if show_creators and asset.creator %}· <i class="iconoir iconoir-user"></i> {{ asset.creator }}{% endif %}
```

No `ai_label.j2`. This is human attribution; the AI-transparency rule applies
to machine-generated output only.

## Credits page

`credits.creators: []` is added to `resources/defaults.yaml` (beside
`travellers`) and to the `credits` block in `resources/config_schema.yaml`,
which is `additionalProperties: false` and so must list it explicitly.

`task_build_credits_page` (`siteTask.py:364`) passes:

```python
creators=sorted(
    (set(self.config["credits"]["creators"]) | self.db.distinct_creators())
    - {None}
)
```

`travellers` keeps its own section — who travelled and who authored are
different claims. That task already carries `uptodate=[False]`, so a
config-only change to `creators` still rebuilds the page.

`credits.j2:9` replaces the placeholder comment:

```jinja
{% if creators %}
## {{ strings.credits_creators }}

{{ creators | join(", ") }}

{% endif %}
```

### New string

`credits_creators` must be added in four places:

1. `resources/defaults.yaml` strings block: `credits_creators: null`
2. `resources/config_schema.yaml` strings properties:
   `credits_creators: {$ref: "#/definitions/customString"}`
3. `locale/en/LC_MESSAGES/messages.po` — `"Creators"`
4. `locale/de/LC_MESSAGES/messages.po` — `"Urheber*innen"`

then `task translate`, or pre-commit fails on translation freshness.

## Gender-neutral German

Nothing in the repository records a convention; the only existing person-noun
is `credits_travellers` → `"Reisende"`. The rule this spec establishes, to be
added to the i18n section of `CLAUDE.md`:

> Prefer neutral formulations in German strings — substantivierte Partizipien
> (`Reisende`, `Mitwirkende`), abstract nouns (`Leitung`), or reformulation.
> Where a gendered noun is unavoidable, use the asterisk (`Urheber*innen`),
> not the colon or Binnen-I.

`Urheber*innen` is the chosen form for `credits_creators`.

## Caption clipping

Adding a creator makes the asset metadata line wrap in the common case. That
line currently **clips its second line** when it wraps, cutting the text
mid-glyph — observed in the lightbox caption.

This must be fixed as part of this work: shipping the creator field without it
turns an edge case into the normal case.

**The cause is not yet diagnosed.** `extra.sass` contains only
`#gallery_captions { display: none }` (line 273); the visible caption box is
styled by mkdocs-glightbox's own CSS. `.gslide-description` itself is not the
culprit: in the compiled `glightbox.min.css` it carries only `flex: 1 0 100%`,
with no height and no overflow rule — the `height`/`max-height`/`overflow`
rules that do exist on `.gslide-description` are scoped under
`.glightbox-mobile` and so do not apply on desktop.

The current hypothesis is layout, not overflow: `.glightbox-container` sets
`overflow: hidden`; `.ginner-container` sets `height: 100vh` and, under
`desc-bottom`, switches to column flex-direction; and `.gslide-image img` gets
`max-height: 97vh` at viewport widths ≥769px. Between them the image can claim
nearly the full height of the container, leaving the caption only whatever
remainder fits inside the hidden-overflow container — enough for one line but
not two. This is **not confirmed** — it is read from the stylesheet, not
measured in a browser — and implementation must verify it against a real build
before proposing a fix, and must not guess at selector names.

Janna runs the example builds; the implementer asks rather than running them.

## Testing

- Calibration stack: creator inherits into subdirectories; a nested
  `calibration.yaml` overrides it; `creator: null` clears it; omitting the key
  inherits.
- Schema: a creator-only `calibration.yaml` validates; `write_calibration_data`
  accepts a partial `{"creator": ...}` dict and preserves existing
  `calibration`/`effects` keys on merge.
- EXIF precedence: calibration wins over `EXIF:Artist`; EXIF fills the gap when
  calibration has none; an empty or whitespace tag counts as absent.
- `distinct_creators()` and the `>= 2` threshold at each row of the visibility
  table, including the mixed `{Bob, None}` case.
- Credits page: union of config and asset creators, deduplicated and sorted,
  with `None` dropped; empty list renders no section.
- Templates: all three render with and without `show_creators`, and an asset
  with no creator renders no separator when `show_creators` is true.
- `calibrate creator`: sets, unsets, errors when given both a name and
  `--unset`, and honours `--dry-run`.

## Documentation

- `docs/reference/configuration.md` — `credits.creators`.
- `CLAUDE.md` — the German-language convention above.
- No task graph change, so `docs/reference/task-dependencies.md` and its
  `.puml` are untouched.

## Out of scope

- Per-asset creator overrides (a sidecar file for one photo). The directory is
  the working granularity; revisit if it proves insufficient.
- Distinguishing creators by medium on the credits page. One flat list; adding
  grouping later needs only a template change, since `asset.type` is retained.
- Linking a creator to a contact, URL, or licence. Names only.
