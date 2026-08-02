"""Inject the dependency credits table into the docs at build time.

Imports mkmapdiary.lib.credits from the source tree, so the documentation
build never installs mkmapdiary or its dependencies.
"""

import logging
from typing import Any

from mkmapdiary.lib.credits import Package, resolved_packages

logger = logging.getLogger(__name__)

MARKER = "<!-- CREDITS_TABLE -->"


def render_table(packages: list[Package]) -> str:
    """Render packages as a markdown table."""
    rows = ["| Name | Version | License |", "| --- | --- | --- |"]
    for package in packages:
        if package.url:
            name = f"[{package.name}]({package.url})"
        else:
            name = package.name
        if package.license is None:
            logger.warning(f"No declared license for {package.name}")
        license_cell = package.license or "not declared"
        rows.append(f"| {name} | {package.version or ''} | {license_cell} |")
    return "\n".join(rows)


def on_page_markdown(
    markdown: str,
    page: Any = None,
    config: Any = None,
    files: Any = None,
) -> str:
    """Replace the marker with the generated table."""
    if MARKER not in markdown:
        return markdown

    # Deliberately unguarded: a failure here should fail the docs build rather
    # than publish a credits page that quietly lost its table.
    packages = resolved_packages()
    return markdown.replace(MARKER, render_table(packages))
