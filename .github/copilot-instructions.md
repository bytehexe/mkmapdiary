# Testing the code

IMPORTANT: Do not run tests yourself! Use these commands:

## Running the unit tests

To run the unit tests for the `llm_dataclass` package, you can use the following command in your terminal:

```bash
hatch test
```

## Type checking

For type checking, you can use `mypy`:

```bash
hatch run types:check
```

## Linting

To lint the code, you can use `ruff`:

```bash
hatch run lint
```

You may also apply automatic fixes with:

```bash
hatch run lint-fix
```

## Formatting

To format the code, you can use `ruff` as well:

```bash
hatch run format
```

If you just want to check the formatting without applying changes, run:

```bash
hatch run format-check
```