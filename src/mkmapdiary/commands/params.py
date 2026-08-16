"""The `-x/--params` option, shared by the commands that accept it."""

from collections.abc import Callable
from typing import Any, TypeVar

import click

# Examples shown in the option's help. The test suite runs every one of them
# through the config loader, so they cannot go stale.
PARAM_EXAMPLES = (
    "features.llms.enabled=false",
    'credits.travellers=["Ada", "Bob"]',
    "features.geo_correlation.max_time_diff=!duration 5 minutes",
)

PARAM_HELP = (
    "Set a configuration parameter; may be given more than once. "
    "Format: key=value, with dot notation for nested keys. The value is "
    "parsed as YAML, so lists, mappings, booleans and the !duration, "
    "!distance and !auto tags all work. Examples: " + "; ".join(PARAM_EXAMPLES) + "."
)

F = TypeVar("F", bound=Callable[..., Any])


def validate_param(
    ctx: click.Context, param: click.Parameter, value: tuple[str, ...]
) -> tuple[str, ...]:
    for val in value:
        if "=" not in val:
            raise click.BadParameter("Parameters must be in the format key=value")
    return value


def params_option(command: F) -> F:
    """Add the `-x/--params` option to a command."""
    option = click.option(
        "-x",
        "--params",
        multiple=True,
        callback=validate_param,
        type=str,
        help=PARAM_HELP,
    )
    return option(command)  # type: ignore[no-any-return]
