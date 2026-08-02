# Testing the code

IMPORTANT: Do not invent your own commands! Use these:

## Running the unit tests

To run the unit tests for the `mkmapdiary` package, you can use the following command in your terminal:

```bash
hatch test
```

To run a single file or a single test:

```bash
hatch test tests/test_rank.py
hatch test tests/test_rank.py::test_calculate_rank
```

Slow tests are excluded in the pre-commit hook via a marker; to do the same manually:

```bash
hatch test -- -m "not slow"
```

## Type checking

For type checking, you can use `mypy`:

```bash
hatch run types:check
```

## Linting

To lint the code, you can use `ruff`:

```bash
hatch run ruff:ruff check .
```

You may also apply automatic fixes with:

```bash
task fix
```

## Formatting

To format the code, you can use `ruff` as well:

```bash
hatch run ruff:ruff format .
```

If you just want to check the formatting without applying changes, run:

```bash
hatch run ruff:ruff format --check .
```

## Everything at once

To run the full gate (yamllint, ruff check, ruff format check, mypy, unit tests,
translation freshness) exactly as the pre-commit hook does:

```bash
task test
```
