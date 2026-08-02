# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Existing agent rules

The repository already carries Copilot instructions; they are imported here:

@.github/copilot-instructions.md

## Commands

Python envs are managed by **hatch** (never invoke `pip`/`venv` directly). Common tasks are
also wrapped as [taskipy](https://taskipy.github.io/) tasks — `task --list`.

```bash
hatch test                                   # pytest via hatch's test runner
hatch test tests/test_rank.py                # single file
hatch test tests/test_rank.py::test_calculate_rank   # single test
hatch test -- -m "not slow"                  # marker filter (what pre-commit runs)
hatch run types:check                        # mypy over src/mkmapdiary and tests
hatch run ruff:ruff check .                  # lint
hatch run ruff:ruff format --check .         # format check
task fix                                     # ruff check --fix + ruff format
task test                                    # == task lint == pre-commit run -a (full gate)
hatch run mkmapdiary --help                  # run the dev version
hatch run min:mkmapdiary --help              # run without optional extras (task run-min)
task translate                               # regenerate locale/*/LC_MESSAGES/messages.mo
hatch run mkdocs:serve                       # serve the project docs (task serve)
```

Pytest markers: `slow`, `local` (the latter must not run in CI).

Environment notes: `default`, `min`, `types` and `hatch-test` all install the project
in dev mode, so imports work without any `PYTHONPATH` — never set one and never call
bare `python3`. `mkdocs` and `ruff` are `detached`, so the project is *not* importable
there; that is deliberate, and it is what makes the `mkdocs` env a faithful stand-in
for the docs CI job, which installs only mkdocs, mkdocs-material and
plantuml-markdown.

Running the generator end to end:

```bash
task demo                                    # generate + build a placeholder project
task example                                 # build ./example with persistent build dir
hatch run mkmapdiary build <src> [<dist>] -B -a   # -B persistent build dir, -a force rebuild
hatch run mkmapdiary build <src> --debug-fast     # skip/replace slow features (dev only)
```

**Commits in this repo are GPG-signed** — `commit.gpgsign` is `true` in the repo-local
config (it is *not* set globally). gpg-agent cannot write inside the command sandbox, so a
sandboxed `git commit` fails to sign. **Always commit with the sandbox disabled**, and this
applies to subagents too: tell any dispatched agent to commit unsandboxed. Never reach for
`--no-gpg-sign` to get past it — that silently leaves an unsigned commit in a signed history,
which then has to be found and amended.

Commits must follow Conventional Commits (enforced by gitlint in the `commit-msg` hook); see
`docs/reference/development/commit-prefixes.md` for the allowed prefixes. Install the hooks
with `pre-commit install` — the pre-commit gate runs yamllint, ruff check, ruff format,
mypy, the test suite, and a translation-freshness check.

## Architecture

mkmapdiary turns a directory of travel sources (images, RAW, audio, text/markdown, GPX,
GPS-logger dumps) into a static MkDocs site. Three layers matter:

**1. Scan → asset registry.** `taskList.py` walks `source_dir`, and for each path uses
`identify` tags (falling back to the file extension) to dispatch to a `handle_<tag>` /
`handle_ext_<ext>` method. Handlers are *generators* that yield `AssetRecord`s
(`lib/asset.py`) and are drained in parallel by `finalize_assets()`. All records live in
`lib/assetRegistry.py::AssetRegistry` — an append/update-only, lock-protected in-memory
store queried by date, type, and geotag. There is no database; the registry *is* the model.

**2. Task graph.** `TaskList` inherits from **all** task mixins at once
(`class TaskList(*tasks)` in `taskList.py`), so every `task_*` method across
`tasks/*.py` becomes a doit task and every mixin shares the same `config`, `db`, `dirs`,
`cache` and `gettext` properties (declared abstract in `tasks/base/baseTask.py`).
`commands/build.py` converts the instance to a dict (`toDict()`) and hands it to doit's
`ModuleTaskLoader`, running threaded. Adding a task = adding a `task_*` method to a mixin
(and registering a new mixin in the `tasks` list). `@create_after(...)` is used where a
task's *set* of subtasks can only be known once an upstream phase finished; barrier tasks
(`pre_gpx`, `end_gpx`, `end_postprocessing`) exist purely to sequence phases.
`docs/reference/task-dependencies.md` documents the full graph.

**3. Postprocessors.** `tasks/postprocessingTask.py` runs two classes of processor from
`postprocessors/`: `SingleAssetPostprocessor`s (one doit subtask per asset, parallel,
mutually order-independent) and `MultiAssetPostprocessor`s (one task, sequential, in list
order, see all assets). LLM work must be multi-asset — inference is not thread-safe here.
Enabling/disabling a postprocessor is done by editing those two lists.

### Adding anything that generates output — use the existing doit structures

Never write a bespoke generation step, a helper that writes files at import time, or a
side effect buried in another task. Everything that produces output is a **doit task**:
add a `task_*` method to the relevant mixin in `tasks/` (or a new mixin registered in
`taskList.py`'s `tasks` list). The pitfalls below have each cost a fix commit already —
they are not theoretical.

- **`task_dep` does not cause rebuilds.** doit's docs are explicit: "Task dependencies
  (`task_dep`) are not used to determine if a task is up-to-date." It orders execution
  and nothing more. A task whose output must be regenerated when an input changes needs
  `file_dep` (or `calc_dep`/`uptodate`) as well.
- **A new page must be added to `task_build_site` in two places.** That task has an
  explicit `_generate_file_deps()` generator *and* a `task_dep` list. The file dependency
  makes mkdocs rebuild when the page changes; the task dependency stops mkdocs running
  before the page exists. Adding only one produces an intermittent failure that a single
  clean build will not reveal. See `b83bd57`, which retrofitted the file dependencies.
- **`uptodate=[False]` for anything whose inputs are not files.** Content driven by
  `config` — strings, feature flags, `credits.travellers` — has no file to hang a
  dependency on, so doit would consider the task up to date and skip it, silently
  shipping a stale page. `6d63f24` flipped four tasks from `uptodate=[True]` to `[False]`
  for exactly this. Most page-building tasks here already use it; follow them.
- **`@create_after` takes exactly one task**, so when work must wait for *several*
  upstream tasks, the codebase inserts a **barrier task** that depends on all of them and
  has downstream tasks `create_after` the barrier. That is the entire purpose of
  `pre_gpx`, `end_gpx` and `end_postprocessing` — `6d63f24` added `end_gpx` and repointed
  four decorators from `geo_correlation` onto it. Depend on the barrier, not on whatever
  individual task happens to run last today.
- **Update `docs/reference/task-dependencies.md`** (and its `.puml`) when you add or
  rewire a task. The graph is documented by hand and drifts otherwise; the history has
  several commits doing nothing but catching it up.

### Cross-cutting concerns

- **Config** is layered in `commands/build.py`: `resources/defaults.yaml` →
  `resources/debug_fast.yaml` (if `--debug-fast`) → user config dir → `<source>/config.yaml`
  → `-x key=value` overrides, merged with `util.deep_update`. Every layer is validated
  against `resources/config_schema.yaml`. `lib/config.py` adds custom YAML tags: `!auto`
  (resolved by `calculate_auto_value`, e.g. locale/timezone/feature autodetection),
  `!duration`, `!distance`. Note that `defaults.yaml` marks several keys
  `# TODO: Not implemented` — check before relying on a flag.
- **Calibration** (`lib/calibration.py`) is a *stack*: a `calibration.yaml` in any source
  subdirectory pushes timezone/offset/effects for that subtree and pops on exit. All
  timestamps go through `BaseTask.calibrate`, which turns a wall-clock reading into a
  `whenever.Instant`. Time handling uses `whenever` (`Instant`/`ZonedDateTime`/`Date`), not
  bare `datetime`.
- **i18n**: user-visible strings are gettext messages in `src/mkmapdiary/locale/`, exposed
  to templates and tasks through `config["strings"]`, overridable per project. **LLM prompts
  are translations too** — `config["llm_prompts"].<key>.translation_key` points at a string,
  and `BaseTask.ai()` formats it, calls ollama, and optionally validates the response
  against a schema. UI strings use an `ui.` prefix. After touching `.po` files run
  `task translate`, or pre-commit fails.
- **Caching**: `lib/cache.py` is a sqlite-backed `MutableMapping` in the platform cache dir;
  reach it via `BaseTask.with_cache(key, fn, *args)`. `--no-cache` swaps in a throwaway db.
  Separately, doit's own up-to-date db lives in the build dir.
- **Directories** are never joined by hand: `lib/dirs.py::Dirs` owns every path
  (`build_dir`, `docs_dir`, `assets_dir`, cache paths, …) and creates them lazily once
  `create_dirs` is enabled.
- **Logging**: module-level `logging.getLogger(__name__)`; pass `extra={"icon": "🚀"}` for
  the console icon and `extra={"is_step": True}` to keep a message visible under `-q`
  (see `util/log.py`). Output rendering, not decoration — keep it consistent.
- **Optional heavy deps** (whisper, torch/piq, onnxruntime) are extras; import them lazily
  inside the feature that needs them and gate on the corresponding `features.*` config,
  as `commands/build.py` and the postprocessors do.
- **Credits**: `lib/credits.py` computes dependency credits at build time — never
  from a committed file. It must import **only the standard library**, because
  `docs/hooks/credits_table.py` imports it with just `src` on `PYTHONPATH` so the
  docs CI never installs mkmapdiary. `installed_packages()` walks the declared
  graph locally (offline, used by journals); `resolved_packages()` resolves from
  the index (used by the docs). CDN library licenses live in `FRONTEND_LICENSES`
  and a test asserts every URL in `site_config.yaml` has an entry.

### Entry points

`mkmapdiary` → `__main__.py` click group with `build`, `config`, `generate-demo`,
`calibrate`, `inspect`. `mkmapdiary-ui` → `ui.py`, a Tkinter front-end that invokes those
same click commands in-process and captures their output.

## REVISIT ON FIRST STABLE RELEASE

Decisions below were made *because* mkmapdiary has never published a
non-prerelease version to PyPI. They are stopgaps, not settled design. When the
first stable release ships, work through this list — grep for
`REVISIT ON FIRST STABLE RELEASE` to find the code sites.

- **`resolved_packages(allow_prerelease=...)` in `lib/credits.py`.** The switch
  adds pip's `--pre` so that a *published* spec like `mkmapdiary[all]` can be
  resolved at all; without a stable release pip refuses to select anything.
  `--pre` is coarse — it opts every transitive dependency into pre-releases too,
  which is a real cost. Once a stable release exists, `resolved_packages(
  "mkmapdiary[all]")` works unflagged and the switch should be reconsidered:
  either dropped, or kept but documented as a deliberate opt-in rather than a
  workaround.
- The default spec stays `".[all]"` regardless. Resolving the local checkout
  describes the commit being documented rather than the last published release,
  which is the better behaviour for a credits page independent of release state.
