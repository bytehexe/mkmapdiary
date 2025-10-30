import logging
import pathlib
import tempfile

import click

from .commands.build import build
from .commands.config import config
from .util.log import StepFilter, setup_logging


@click.group()
@click.option(
    "-v",
    "--verbose",
    count=True,
    help="Increase verbosity level. Can be used multiple times.",
)
@click.option(
    "-q",
    "--quiet",
    count=True,
    help="Decrease verbosity level. Can be used multiple times.",
)
@click.pass_context
def cli(ctx, verbose, quiet):
    """mkmapdiary - Create map diaries from GPS data and notes."""
    # Setup logging first - use temporary directory for log file initially
    with tempfile.TemporaryDirectory() as tmpdir:
        setup_logging(pathlib.Path(tmpdir))

    # Handle verbosity conflicts
    if verbose > 0 and quiet > 0:
        raise click.BadParameter("Cannot use both verbose and quiet options together.")

    # Configure console logging based on verbosity
    console_log = logging.getHandlerByName("console")
    if console_log:
        if quiet == 1:
            console_log.addFilter(StepFilter())
        elif quiet == 2:
            console_log.setLevel(logging.WARNING)
        elif quiet == 3:
            console_log.setLevel(logging.ERROR)
        elif quiet >= 4:
            console_log.setLevel(logging.CRITICAL)

        if verbose == 1:
            console_log.setLevel(logging.DEBUG)
        elif verbose >= 2:
            console_log.setLevel(logging.NOTSET)

    # Store verbosity settings in context for subcommands
    ctx.ensure_object(dict)
    ctx.obj["verbose"] = verbose
    ctx.obj["quiet"] = quiet


# Add subcommands
cli.add_command(build)
cli.add_command(config)


if __name__ == "__main__":
    cli()
