import ast
import sys
from pathlib import Path
from typing import Any

from mkmapdiary.lib.credits import Package

ROOT = Path(__file__).parent.parent


def _load_hook() -> Any:
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


def test_credits_module_imports_only_stdlib() -> None:
    """The docs build imports credits.py without mkmapdiary's dependencies."""
    source = (ROOT / "src" / "mkmapdiary" / "lib" / "credits.py").read_text()

    imported: set[str] = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imported.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            imported.add(node.module.split(".")[0])

    third_party = sorted(imported - sys.stdlib_module_names)

    assert not third_party, (
        f"credits.py must import only the standard library; found: {third_party}"
    )
