import pathlib
import tempfile

import click
import platformdirs

from ..lib.config import write_config
from ..util.log import setup_logging


def validate_param(ctx, param, value):
    for val in value:
        if "=" not in val:
            raise click.BadParameter("Parameters must be in the format key=value")
    return value


@click.command()
@click.option(
    "-x",
    "--params",
    multiple=True,
    callback=validate_param,
    type=str,
    help="Add additional configuration parameter. Format: key=value. Nested keys can be specified using dot notation, e.g., 'features.transcription=False'",
)
@click.option(
    "--user",
    is_flag=True,
    help="Write configuration to the user config file instead of the project config file.",
)
@click.argument(
    "source_dir",
    type=click.Path(path_type=pathlib.Path),
    required=False,
)
def config(params, user, source_dir):
    """Apply configuration from the --params options and write them to config.yaml."""
    # Setup logging first - use temporary directory for log file
    with tempfile.TemporaryDirectory() as tmpdir:
        setup_logging(pathlib.Path(tmpdir))

        if user and source_dir is not None:
            raise click.BadParameter("Source directory cannot be used with --user.")

        if not user and source_dir is None:
            raise click.BadParameter(
                "Source directory is required when not using --user."
            )

        if user:
            source_dir = pathlib.Path(
                platformdirs.user_data_dir("mkmapdiary", "bytehexe")
            )
            source_dir.mkdir(parents=True, exist_ok=True)

        if not source_dir:
            raise click.BadParameter("Could not determine configuration directory.")

        write_config(source_dir, params)
