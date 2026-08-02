"""Inject the dependency credits table into the docs at build time.

Imports mkmapdiary.lib.credits from the source tree, so the documentation
build never installs mkmapdiary or its dependencies.
"""

from typing import Any

from mkmapdiary.lib.credits import Package, resolved_packages

MARKER = "<!-- CREDITS_TABLE -->"


def render_table(packages: list[Package]) -> str:
    """Render packages as a markdown table."""
    rows = ["| Name | Version | License |", "| --- | --- | --- |"]
    for package in packages:
        if package.url:
            name = f"[{package.name}]({package.url})"
        else:
            name = package.name
        rows.append(f"| {name} | {package.version or ''} | {package.license or ''} |")
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
