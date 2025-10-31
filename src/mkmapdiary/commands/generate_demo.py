import pathlib

import click

from ..generate_demo import generate_demo_data


@click.command()
@click.argument(
    "source_dir",
    type=click.Path(path_type=pathlib.Path),
    required=True,
)
def generate_demo(source_dir):
    """Generate demo data in the source directory.

    This command generates demo data for testing purposes only.
    The target directory must be empty.

    SOURCE_DIR: Directory where demo data will be generated (must be empty)
    """
    if not source_dir:
        raise click.BadParameter("Source directory is required.")

    generate_demo_data(source_dir)
