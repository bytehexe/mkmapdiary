import pathlib
import sys
import tempfile
from collections.abc import Sequence

import click
import platformdirs
import yaml

from ..lib.config import install_translations, resolve_config, write_config
from ..lib.dirs import Dirs
from .params import params_option


def show_config(source_dir: pathlib.Path | None, params: Sequence[str]) -> None:
    """Print the effective configuration as YAML to stdout.

    Without a source directory only the defaults, the user configuration and
    the params are merged, which is the configuration any project without its
    own `config.yaml` would see.
    """
    with tempfile.TemporaryDirectory() as tempdir:
        # No build happens here, so the build and dist directories are unused
        tempdir_path = pathlib.Path(tempdir)
        dirs = Dirs(source_dir or tempdir_path, tempdir_path, tempdir_path, False)

        config_data = resolve_config(dirs, params)
        install_translations(config_data, dirs.locale_dir)

    yaml.dump(dict(config_data), sys.stdout, sort_keys=False, allow_unicode=True)


@click.command()
@params_option
@click.option(
    "--user",
    is_flag=True,
    help="Write configuration to the user config file instead of the project config file.",
)
@click.option(
    "--get",
    is_flag=True,
    help="Print the effective configuration, including the defaults and any --params, as YAML to stdout instead of writing it.",
)
@click.argument(
    "source_dir",
    type=click.Path(path_type=pathlib.Path),
    required=False,
)
def config(
    params: tuple[str, ...], user: bool, get: bool, source_dir: pathlib.Path | None
) -> None:
    """Apply configuration from the --params options and write them to config.yaml.

    With --get nothing is written; the effective configuration is printed
    instead.
    """
    # Logging is now set up at the group level

    if user and source_dir is not None:
        raise click.BadParameter("Source directory cannot be used with --user.")

    if not user and source_dir is None:
        raise click.BadParameter("Source directory is required when not using --user.")

    if source_dir is not None and not source_dir.is_dir():
        raise click.BadParameter(
            f"Source directory '{source_dir}' does not exist or is not a directory."
        )

    if get:
        show_config(source_dir, params)
        return

    if user:
        source_dir = pathlib.Path(
            platformdirs.user_config_dir("mkmapdiary", "bytehexe")
        )
        source_dir.mkdir(parents=True, exist_ok=True)

    if not source_dir:
        raise click.BadParameter("Could not determine configuration directory.")

    write_config(source_dir, params)
