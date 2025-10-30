import click

from .commands.build import build
from .commands.config import config


@click.group()
def cli():
    """mkmapdiary - Create map diaries from GPS data and notes."""


# Add subcommands
cli.add_command(build)
cli.add_command(config)


if __name__ == "__main__":
    cli()
