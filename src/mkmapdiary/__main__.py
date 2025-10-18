import click
import pathlib
import yaml

from .taskList import TaskList
from . import util
from doit.api import run_tasks
from doit.doit_cmd import DoitMain
from doit.cmd_base import ModuleTaskLoader
from tabulate import tabulate
from .cache import Cache
import os
import locale
import gettext
import tempfile

import sys


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
    "-b",
    "--build-dir",
    type=click.Path(path_type=pathlib.Path),
    help="Path to the build directory (implies -B; defaults to a temporary directory)",
)
@click.option(
    "-B",
    "--persistent-build",
    is_flag=True,
    help="Uses a persistent build directory",
)
@click.option(
    "-a",
    "--always-execute",
    is_flag=True,
    help="Always execute tasks, even if up-to-date. Only relevant with persistent build directory.",
)
@click.option(
    "-n",
    "--num-processes",
    default=os.cpu_count(),
    type=int,
    help="Number of parallel processes to use",
)
@click.option("-v", "--verbose", is_flag=True, help="Enable verbose output")
@click.option("--no-cache", is_flag=True, help="Disable cache in the home directory (not recommended)")
@click.argument(
    "source_dir",
    type=click.Path(path_type=pathlib.Path),
)
@click.argument(
    "dist_dir",
    type=click.Path(path_type=pathlib.Path),
    required=False,
)
def start(
    source_dir,
    dist_dir,
    build_dir,
    persistent_build,
    **kwargs,
):
    if dist_dir is None:
        dist_dir = source_dir.with_name(source_dir.name + "_dist")

    if persistent_build and build_dir is None:
        build_dir = source_dir.with_name(source_dir.name + "_build")

    main_exec = lambda: main(
        dist_dir=dist_dir,
        build_dir=build_dir,
        source_dir=source_dir,
        **kwargs,
    )

    if build_dir is None:
        with tempfile.TemporaryDirectory() as tmpdirname:
            build_dir = pathlib.Path(tmpdirname)
            main_exec()
    else:
        main_exec()


def main(
    dist_dir,
    build_dir,
    params,
    source_dir,
    always_execute,
    num_processes,
    verbose,
    no_cache,
):

    click.echo("Generating configuration ...")

    script_dir = pathlib.Path(__file__).parent

    # Load config defaults
    default_config = script_dir / "extras" / "defaults.yaml"
    config_data = yaml.safe_load(default_config.read_text())

    # Load local user configuration
    user_config_file = pathlib.Path.home() / f".mkmapdiary/config.yaml"
    if user_config_file.exists():
        config_data = util.deep_update(
            config_data, yaml.safe_load(user_config_file.read_text())
        )

    # Load project configuration file if provided
    project_config_file = source_dir / "config.yaml"
    if project_config_file.is_file():
        config_data = util.deep_update(
            config_data, yaml.safe_load(project_config_file.read_text())
        )

    # Override config with params
    for param in params:
        key, value = param.split("=", 1)
        key = key.split(".")
        d = config_data
        for k in key[:-1]:
            d = d.setdefault(k, {})
        d[key[-1]] = yaml.safe_load(value)

    # Load gettext
    localedir = script_dir / "locale"
    lang = gettext.translation(
        "messages",
        localedir=str(localedir),
        languages=[config_data["locale"].split("_")[0]],
        fallback=True,
    )
    lang.install()
    _ = lang.gettext

    # Load defaults for unset parameters
    config_data.setdefault("site_name", _("Travel Diary"))
    config_data.setdefault("home_title", _("Home"))
    config_data.setdefault("gallery_title", _("Gallery"))
    config_data.setdefault("map_title", _("Map"))
    config_data.setdefault("journal_title", _("Journal"))
    config_data.setdefault("days_title", _("Days"))
    config_data.setdefault("audio_title", _("Audio"))

    # Set locale
    locale.setlocale(locale.LC_TIME, config_data["locale"])

    # Feature checks
    features = config_data["features"]
    if features["transcription"] == "auto":
        try:
            import whisper

            features["transcription"] = True
        except ImportError:
            features["transcription"] = False
    elif features["transcription"] is True:
        try:
            import whisper
        except ImportError:
            click.echo(
                "Error: Transcription feature requires the 'whisper' package to be installed."
            )
            sys.exit(1)

    click.echo("Preparing directories ...")
    # Sanity checks
    if not source_dir.is_dir():
        click.echo(
            f"Error: Source directory '{source_dir}' does not exist or is not a directory."
        )
        sys.exit(1)
    if build_dir.is_file():
        click.echo(f"Error: Build directory '{build_dir}' is a file.")
        sys.exit(1)
    if dist_dir.is_file():
        click.echo(f"Error: Distribution directory '{dist_dir}' is a file.")
        sys.exit(1)
    if build_dir == dist_dir:
        click.echo("Error: Build and distribution directories must be different.")
        sys.exit(1)
    if build_dir == source_dir:
        click.echo("Error: Build and source directories must be different.")
        sys.exit(1)
    if dist_dir == source_dir:
        click.echo("Error: Distribution and source directories must be different.")
        sys.exit(1)
    if (
        build_dir.is_dir()
        and any(build_dir.iterdir())
        and not (build_dir / "mkdocs.yml").is_file()
    ):
        click.echo(
            f"Error: Build directory '{build_dir}' is not empty and does not contain a mkdocs.yml file."
        )
        sys.exit(1)
    if (
        dist_dir.is_dir()
        and any(dist_dir.iterdir())
        and not (dist_dir / "index.html").is_file()
    ):
        click.echo(
            f"Error: Distribution directory '{dist_dir}' is not empty and does not contain an index.html file."
        )
        sys.exit(1)

    # Create directories
    if not dist_dir.is_dir():
        dist_dir.mkdir(parents=True, exist_ok=True)
    if not build_dir.is_dir():
        build_dir.mkdir(parents=True, exist_ok=True)

    # Clean build directory if needed
    if always_execute:
        util.clean_dir(build_dir)

    click.echo("Generating tasks ...")

    if no_cache:
        cache = {}
    else:
        cache = Cache(pathlib.Path.home() / ".mkmapdiary" / "cache.sqlite")

    taskList = TaskList(config_data, source_dir, build_dir, dist_dir, cache)

    n_assets = taskList.db.count_assets()
    click.echo(f"Found {n_assets} assets" + (":" if n_assets > 0 else "."))
    if n_assets > 0:
        print(tabulate(*taskList.db.dump()))

    proccess_args = []
    if always_execute:
        proccess_args.append("--always-execute")
    if num_processes > 0:
        proccess_args.append(f"--process={num_processes}")
    if verbose:
        proccess_args.extend(["-v", "2"])
    proccess_args.append("--parallel-type=thread")

    click.echo("Running tasks ...")

    doit_config = {
        "GLOBAL": {
            "backend": "sqlite3",
            "dep_file": str(build_dir / "doit.db"),
        }
    }
    exitcode = DoitMain(
        ModuleTaskLoader(taskList.toDict()),
        config_filenames=(),
        extra_config=doit_config,
    ).run(proccess_args)
    click.echo("Done.")
    sys.exit(exitcode)


if __name__ == "__main__":
    start()
