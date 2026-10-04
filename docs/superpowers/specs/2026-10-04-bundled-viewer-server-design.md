# Bundled Viewer Server — Design

## Problem

mkmapdiary generates fully static, `file://`-browsable journal sites (`use_directory_urls:
False`, the `offline` mkdocs plugin). The map widget embeds OpenStreetMap's Standard tile
layer (`geo.js`) directly at `{s}.tile.openstreetmap.org`. OSMF has stepped up enforcement
of its [tile usage policy](https://operations.osmfoundation.org/policies/tiles/): web
applications must send a valid `Referer` header, and `file://` pages never send one, by
browser spec, regardless of any header or meta tag mkmapdiary's code could set. The result
is the tile layer now renders as OSMF's "Access blocked" placeholder tile for anyone
opening a generated journal directly, which is the project's primary, intended usage mode.

There is no header-level fix: this is not a false positive, and no change to request
headers from a `file://` origin can produce a Referer that doesn't exist. The only way to
satisfy OSM's check is to serve the page over `http(s)://` instead of `file://`.

## Goals

- Restore a working interactive map for the default, zero-setup case (opening a generated
  journal directly, on any of Windows/macOS/Linux, with no technical background assumed of
  the viewer).
- Keep the output directory fully self-contained and portable: it must work after being
  copied to a USB stick or a different machine than the one it was built on, with nothing
  installed beyond what's already bundled.
- Make it unambiguous what to run, especially for Windows users.

## Non-goals (deferred to the follow-up "tile download pipeline" spec)

- Changing which tile URL `geo.js` points at.
- Downloading/baking tiles at build time.
- Any configuration of `tile_server`, download mode (`feedable`/`assume-complete`), or the
  safeguard against bulk-downloading from OSM's own CDN.

This spec covers only: giving the existing, unchanged tile layer a valid `Referer` by
serving the generated site from `http://127.0.0.1` instead of `file://`. It does not change
what is requested, only how the page that makes the request is served.

## Design

### Binary acquisition & caching

A new module (alongside `lib/cache.py`/`lib/dirs.py`) downloads pinned-version
[`miniserve`](https://github.com/svenstaro/miniserve) (MIT licensed) release binaries for
Linux, macOS, and Windows from GitHub Releases, verifies each against a SHA256 checksum
pinned in mkmapdiary's own source, and caches the verified binaries locally.

- Exact version + checksums are pinned as a constant in mkmapdiary's source, so a version
  bump is an explicit, reviewable code change — not a moving target resolved at build time.
- Download uses the same atomic pattern `poiidx.Pbf` already uses: write to a temp file in
  the cache directory, then `os.replace` into place, so an interrupted download can't poison
  the cache for a later run.
- Cache location: `Dirs.user_cache_dir / "viewer_server"` (`lib/dirs.py::Dirs`), following
  the existing `region_cache_dir` precedent of a named subdirectory under mkmapdiary's own
  `platformdirs`-based cache root. This is mkmapdiary's own cache namespace, separate from
  `poiidx`'s (`~/.cache/poiidx/`).
- Wired in as a doit task with `file_dep`/`uptodate` keyed on the cached file's presence and
  checksum, so it only re-downloads on a cache miss or checksum mismatch — not on every
  build (per the task-graph rules in the project's `CLAUDE.md`).

### Build output layout

The existing flat output directory moves into a subdirectory (working name `_site/`) inside
the build's dist directory. The top level of the output then contains only:

- `Open on Windows.bat`
- `Open on Mac.command`
- `Open on Linux.sh`
- `_site/` (the actual journal content, previously the top level)
- `_site/.server/` containing the three cached `miniserve` binaries (all three are always
  bundled, since the build machine doesn't know which OS the recipient will use) plus their
  license text

A new doit task copies the cached, verified binaries and renders the three launcher scripts
into the output on every build (file-copy task, same shape as the existing
`task_copy_simple_asset` in `siteTask.py`).

### Launcher behavior

All three launchers implement the same sequence, each in its native scripting language
(Batch, a macOS `.command` shell script, a POSIX shell script):

1. Resolve to the launcher's own directory (so it works regardless of the working directory
   it's invoked from).
2. Try a short sequence of candidate ports — `51342`, `51343`, `51344`, `51345`, `51346` —
   using a native connection test per platform (PowerShell on Windows; `/dev/tcp` or `nc` on
   macOS/Linux), and use the first one found free. These are drawn from the IANA
   dynamic/private port range (49152–65535) specifically to avoid collisions with common
   local dev tooling (`3000`, `5000`, `8000`, `8080`, `8888`, etc. are all frequently already
   bound by other installed software).
3. Start the platform's cached `miniserve` binary bound to `127.0.0.1:<port>` only — never
   `0.0.0.0` — serving `_site/`, with directory listing disabled and `index.html` as the
   entry point.
4. Poll (short retry-connect loop) until the server is actually accepting connections — not
   merely until the process has started — before proceeding.
5. Open the system default browser at `http://127.0.0.1:<port>/`.
6. Print a clear, visible message identifying the URL and stating that closing the window
   stops the server (e.g. "Your travel journal is running at http://127.0.0.1:<port>/ —
   close this window to stop viewing.").
7. Run in the foreground of the console window for the server process's lifetime, so closing
   the window terminates the server — no separate stop mechanism needed.

If every candidate port is unavailable, the launcher prints a clear failure message naming
the attempted ports rather than failing silently.

Dynamic port selection via native per-platform connection tests is the chosen approach over
a single fixed port; if it proves too fragile per-platform during implementation, falling
back to one fixed port is a small, isolated change to the launcher scripts, not a design
change.

### Config

New flag, following the existing `features.<name>.enabled` convention used by
`poi_detection`, `llms`, `transcription`, etc. (`resources/config_schema.yaml`,
`resources/defaults.yaml`):

```yaml
features:
  viewer_server:
    enabled: true
```

When `false`, the build produces exactly today's output: a flat directory with `index.html`
at the top, no launchers, no bundled binaries. This is a clean, regression-free fallback —
nothing about the existing `file://`-browsable behavior changes when the feature is off.

### Licensing & attribution

`miniserve` is MIT licensed, which permits redistribution inside the generated output.
Because the binary is now bundled and shipped to every viewer of every generated journal —
not merely invoked as an external system dependency the way `ffmpeg`/`gpsbabel`/PostgreSQL
are (`docs/reference/dependencies.md`) — it needs an attribution entry, the same obligation
class as the CDN-sourced frontend libraries tracked via `FRONTEND_LICENSES` in
`lib/credits.py`. The existing `FRONTEND_LICENSES` mechanism is specifically keyed off CDN
URLs parsed from `site_config.yaml` and does not fit a vendored binary as-is; the
implementation plan should define a credits entry for `miniserve` that is visible on the
generated credits page, in the same spirit as `FRONTEND_LICENSES`, whether that's a small
parallel list or an extension of the existing one. A test should assert this entry exists,
mirroring the existing test that asserts every CDN URL in `site_config.yaml` has a
`FRONTEND_LICENSES` entry.

### Documentation

`docs/reference/task-dependencies.md` and its `.puml` get updated for the new task(s), per
the project's task-graph documentation rule. `docs/reference/dependencies.md` is not
affected (the binaries are fetched by mkmapdiary itself, not a system dependency the user
installs).

## Testing

- Unit tests for the binary download/cache/checksum-verification module (including the
  atomic-write and checksum-mismatch paths), following `poiidx.Pbf`'s test patterns.
- Unit tests for the doit task wiring (file_dep/uptodate behavior on cache hit vs. miss).
- A test asserting the `miniserve` credits/license entry exists and renders.
- Launcher scripts are shell scripts and not natively unit-testable the way Python is;
  verification is manual, cross-platform (Windows/macOS/Linux), run before this is
  considered done: double-click each launcher, confirm port selection, browser auto-open,
  server reachability, and that closing the console window stops the server.

## Open items for the implementation plan

- Exact mechanism for the `miniserve` credits/license entry (parallel list vs. extending
  `FRONTEND_LICENSES`).
- Exact output subdirectory name (`_site/` is a working name, not finalized).
- Exact module/file names and where the new doit task(s) live among the existing `tasks/`
  mixins.
