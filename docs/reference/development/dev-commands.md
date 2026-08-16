# Dev commands

## Common commands

Most commonly used development commands are also available as [taskipy](https://taskipy.github.io/) tasks. You can run them via:

```
task <taskname>
```

Run `task --list` to see all available tasks.

Python environments are managed by [hatch](https://hatch.pypa.io/); never invoke `pip` or
create a virtualenv by hand.

## Running the dev version

```bash
# Show help
hatch run mkmapdiary --help

# Build a project  
hatch run mkmapdiary build source_dir

# Configure a project
hatch run mkmapdiary config -x key=value source_dir

# Build without the optional extras, to check the degraded path
hatch run min:mkmapdiary build source_dir

# Skip or replace the slow features while iterating (development only)
hatch run mkmapdiary build source_dir --debug-fast

# Generate and build the demo project
task demo
```

## Tests, types and linting

```bash
hatch test                          # the whole suite
hatch test tests/test_rank.py       # one file
hatch test -- -m "not slow"         # what the pre-commit hook runs
hatch run types:check               # mypy
hatch run ruff:ruff check .         # lint
hatch run ruff:ruff format --check . # formatting
task fix                            # apply ruff fixes and reformat
task test                           # the full pre-commit gate
```

The markers are `slow` and `local`; `local` tests must not run in CI.

## Translations

User-visible strings — including the LLM prompts — are gettext messages in
`src/mkmapdiary/locale/`. After editing a `.po` file, regenerate the compiled catalogs,
or the pre-commit freshness check fails:

```bash
task translate
```

## Documentation

```bash
hatch run mkdocs:serve              # serve the docs locally (task serve)
```

The `mkdocs` environment is detached and does not install mkmapdiary, which makes it a
faithful stand-in for the docs CI job.

## Pruning the enviroments

```
hatch env prune
```