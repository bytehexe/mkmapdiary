# License hygiene: credits pages and GPL removal

**Date:** 2026-08-02
**Status:** Approved, ready for implementation planning

## Context

mkmapdiary is distributed under PolyForm Noncommercial 1.0.0. Three gaps
motivated this work:

1. The project docs name the license but credit no dependencies.
2. Generated journals credit nobody — not the travellers, not mkmapdiary, not
   the open source software they load.
3. A dependency audit run during design found a GPLv3 package in the import
   graph, which conflicts with PolyForm Noncommercial.

The audit was run against the existing development environment using
`importlib.metadata` (135 installed distributions). Its findings are recorded in
the appendix and drove several decisions below.

## Constraints

These are fixed and shaped the design:

- **The docs CI must not install mkmapdiary.** `.github/workflows/publish-docs.yml`
  installs only `mkdocs` and `mkdocs-material`. Installing the `all` extra pulls
  torch and the CUDA stack; the local environment measures 9.8 GB.
- **No committed generated data file.** A snapshot of dependency data goes stale
  silently, and stale credits are worse than absent credits.
- **Journal builds must work offline.** mkmapdiary's stated selling point is
  producing sites that need no server; a credits page must not introduce a
  network dependency into a build.

## Decisions

| Question | Decision |
| --- | --- |
| Where does dependency data come from? | Computed at page-build time by a generator shipped inside the package. No committed file. |
| Journal credits data source | The local environment via `importlib.metadata`. No network. |
| Docs credits data source | `pip install --dry-run --report`, resolving `mkmapdiary[all]` from the index. |
| What does a journal credit? | Travellers, mkmapdiary + license, software that ships or loads in the output, plus a link to the docs for the full Python toolchain. |
| Transitive dependencies | Included, including the 17 NVIDIA packages that arrive with torch. |
| Travellers config | A plain list of names. |
| tkcalendar | Removed; the widget is replaced. |

## Non-goals

- **Photographer credits.** The journal template reserves a place for them, but
  deriving photographers from asset metadata is a separate feature.
- **Versioned docs.** A journal links to the current docs credits page, which
  reflects the latest dependency set rather than the version that built that
  journal. Accepted as approximate.
- **Relicensing anything.** PolyForm Noncommercial for mkmapdiary and MIT for
  poiidx both stay as they are.

## Design

### 1. `src/mkmapdiary/lib/credits.py`

The generator, shipped with the package.

```python
@dataclass(frozen=True)
class Package:
    name: str
    version: str | None
    license: str | None
    url: str | None

def installed_packages(root: str = "mkmapdiary") -> list[Package]: ...
def resolved_packages(spec: str = "mkmapdiary[all]") -> list[Package]: ...
def frontend_libraries(site_config: Mapping[str, Any]) -> list[Package]: ...
```

**This module must import only the standard library.** That is what lets the
docs hook import it from the source tree via `PYTHONPATH=src` without installing
mkmapdiary. `src/mkmapdiary/__init__.py` is empty and `src/mkmapdiary/lib/` has
no `__init__.py`, so the import path works today; a test guards the constraint.

`installed_packages` walks `Requires-Dist` outward from the root distribution
using `importlib.metadata`, honouring extras markers. Traversing the declared
graph rather than listing the environment is deliberate: it excludes packages
that happen to be installed but are not dependencies. The audit found
`pyinstaller` (GPLv2) in the environment, declared by nothing.

License normalisation resolves in a fixed order, first hit wins:

0. An **election table** in the module, keyed by distribution name
1. `License-Expression` metadata field (PEP 639)
2. `License :: ...` classifiers, joined with `; `
3. `License` field, when it is a short identifier rather than embedded license text
4. `None`

The election table exists because dual-licensed packages offer a choice that
metadata cannot express. `PyExifTool` is licensed `GPLv3+ or BSD` at the
recipient's option and declares both as classifiers; joining them would render
`BSD License; GNU General Public License v3 or later (GPLv3+)`, which reads as a
conflict rather than a choice. mkmapdiary elects **BSD**, and the table records
that election with a comment stating the reason. Entries are only added for
genuine dual licenses, never to paper over an unclear one.

`resolved_packages` shells out to `pip install --dry-run --report -` and parses
the JSON report. PyPI serves PEP 658 metadata files, so pip fetches each wheel's
`METADATA` rather than the wheel — torch costs kilobytes. Used only by the docs
hook.

### 2. Frontend libraries

`frontend_libraries` parses the CDN URLs already declared in
`resources/site_config.yaml` under `extra_css` and `extra_javascript`. A URL of
the form `https://unpkg.com/leaflet@1.9.4/dist/leaflet.js` yields both name and
version, so those two fields can never drift from what the page actually loads.

Licenses and homepages are not derivable from a URL, so they come from a
constant table in the module — the single hand-maintained piece of data in this
design. Its staleness gate is a unit test asserting that **every** CDN URL in
`site_config.yaml` has a matching table entry, so adding a library without
crediting it fails the test suite instead of shipping an incomplete page.

Current entries: leaflet, leaflet.markercluster, leaflet.photo,
leaflet.awesome-markers, leaflet-gpx, leaflet-gesture-handling,
leaflet.fullscreen, jquery, justifiedGallery, iconoir.

### 3. Docs credits page

`docs/reference/credits.md` holds hand-written prose: the license statement, the
`Required Notice:` line, and an acknowledgement of poiidx. A mkdocs hook injects
a generated dependency table built from `resolved_packages`.

Changes to `.github/workflows/publish-docs.yml`: the build gains
`PYTHONPATH=src:docs`. The `pip install` line is unchanged.

If resolution fails — no network, index error, malformed report — **the docs
build fails**. Publishing a credits page that silently lost its table is worse
than a red build.

`docs/reference/index.md` gains a link to the page.

### 4. Journal credits page

A `task_build_credits_page` in `tasks/siteTask.py`, sequenced after
`end_postprocessing`, renders a new `templates/credits.j2` to
`docs_dir/credits.md`. Section order:

1. **Travellers** — from `credits.travellers`; section omitted when the list is empty
2. *Photographers* — not implemented; the template reserves the position
3. **Made with** — mkmapdiary, its version, and a link to PolyForm Noncommercial 1.0.0
4. **Open source software** — `frontend_libraries`, plus an explicit list of the
   packages whose *output* is copied into `_dist`: `mkdocs-material` and
   `mkdocs-glightbox`. Their versions and licenses are read from the local
   environment via `installed_packages`. The list is explicit rather than
   derived, because "does this package's output end up in the site" is not
   answerable from metadata; a comment in the module records why each entry is
   there.
5. **Toolchain** — a sentence linking to the docs credits page

`copyright` in `site_config.yaml` gains a link to the page.

Credits must never fail a journal build. A distribution that cannot be read is
logged at warning level and skipped.

### 5. Configuration

New top-level `credits` block in `resources/defaults.yaml`:

```yaml
credits:
  travellers: []
```

`resources/config_schema.yaml` gains a matching definition: an array of strings.
Accepting an object per entry later — for links or roles — is a backwards
compatible schema change if it is ever wanted.

### 6. Translations

New keys in `defaults.yaml` under `strings`, each defaulting to `null` so
gettext supplies the translation: `credits_title`, `credits_travellers`,
`credits_made_with`, `credits_software`, `credits_toolchain`.

German and English `.po` files gain entries; `task translate` regenerates the
`.mo` files. The `translation-files` pre-commit hook enforces freshness.

### 7. tkcalendar removal

The GPLv3 conflict. Exposure is one import and one call site.

- Remove `tkcalendar` from the `ui` and `all` extras in `pyproject.toml`
  (lines 89 and 103).
- Remove the import at `ui.py:22`.
- Replace `DateEntry` at `ui.py:974` with a `ttk.Entry` carrying ISO-date
  validation. The calendar popup is the only functionality lost.
- `babel` was pulled in solely as tkcalendar's dependency and leaves with it.

The `[tool.hatch.envs.licenses]` environment and its `pip-licenses` dependency
become unused and are removed. It inherits `features = ["all"]`, so invoking it
would build a second ~10 GB environment; `importlib.metadata` supersedes it.

## Testing

| Area | Test |
| --- | --- |
| License normalisation | Each of the four resolution steps, including embedded license text falling through to `None` |
| Graph traversal | A synthetic graph proves undeclared distributions are excluded |
| Stdlib-only constraint | Importing `credits.py` with only `src` on the path succeeds |
| CDN parsing | Name and version extracted from unpkg, jsdelivr and cdnjs URL shapes |
| Staleness gate | Every CDN URL in `site_config.yaml` has a license table entry |
| Template | Renders with populated travellers and with an empty list |
| `resolved_packages` | Parses a canned report JSON fixture |

No test performs network access.

## Follow-ups

- **Photographer credits**, per the non-goals above.

## Appendix: audit findings

From `importlib.metadata` over the development environment, 135 distributions.

**Acted on in this spec**

- `tkcalendar` 1.6.1 — GPLv3. Declared in the `ui` and `all` extras, imported at
  `ui.py:22`, used once at `ui.py:974`. PolyForm Noncommercial imposes a
  field-of-use restriction; GPLv3 section 7 forbids imposing further
  restrictions. mkmapdiary does not ship tkcalendar, but declaring it a required
  dependency of an extra means `pipx install mkmapdiary[all]` assembles the
  combination by design, which weakens a mere-aggregation argument.

**Verified during design, resolved**

- `PyExifTool` 0.5.6 declares both `BSD License` and `GPLv3+` classifiers, which
  initially looked like a second GPL problem. Its `LICENSE` file resolves it:
  the package may be used "under the terms of the GNU General Public License
  … version 3 … or the BSD licence", and the wheel ships both `COPYING.BSD` and
  `COPYING.GPL`. This is a dual license, not a conflict. mkmapdiary elects BSD,
  recorded in the election table described in section 1. The exiftool binary
  itself is invoked as a subprocess and is unaffected either way.

**Noted, no action**

- `pyinstaller` 6.17.0 (GPLv2) is installed but declared by nothing. Excluded by
  graph traversal; would have been published by an environment dump.
- `psycopg2-binary` 2.9.11 — LGPL with exceptions, arriving via poiidx.
  Unmodified library use is fine.
- 17 NVIDIA packages are `Other/Proprietary License`, arriving with torch.
  Included in credits deliberately.
- `certifi`, `pathspec`, `tqdm` — MPL-2.0, file-level copyleft, unmodified.

**poiidx** (`../poiidx`, a sibling project by the same author) is MIT. Its
dependencies are `coordinate-parser` MIT, `peewee` MIT, `requests` Apache-2.0,
`osmium` BSD-2-Clause, `psycopg2-binary` LGPL-with-exceptions, plus shapely,
pyyaml and platformdirs. MIT flowing into a PolyForm Noncommercial consumer is
permitted; no conflict.

**On obligation versus courtesy:** the attribution clauses in MIT, BSD and
Apache-2.0 attach to redistribution. mkmapdiary does not redistribute its Python
dependencies — pip fetches each from PyPI — so these credits are good practice
rather than a license obligation. The exception is software copied into the
generated `_dist` directory, where mkdocs-material and glightbox assets become
real files. CDN-loaded libraries are linked, not redistributed.

This appendix is a snapshot taken on 2026-08-02 for design purposes. It is not a
data source for the generated pages; those compute their own data at build time.
