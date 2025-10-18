import click
import pathlib
import yaml

from .taskList import TaskList
from doit.api import run_tasks
from doit.doit_cmd import DoitMain
from doit.cmd_base import ModuleTaskLoader
from pydantic.utils import deep_update
from tabulate import tabulate
from .cache import Cache
import os
import locale
import gettext

import sys


def validate_param(ctx, param, value):
    for val in value:
        if "=" not in val:
            raise click.BadParameter("Parameters must be in the format key=value")
    return value


@click.command()
@click.option(
    "-C",
    "--change-dir",
    default=".",
    type=click.Path(path_type=pathlib.Path),
    help="Change to this directory before doing anything",
)
@click.option(
    "-d",
    "--dist-dir",
    default="dist",
    type=click.Path(path_type=pathlib.Path),
    help="Path to distribution directory",
)
@click.option(
    "-x",
    "--params",
    multiple=True,
    callback=validate_param,
    type=str,
    help="Additional parameters",
)
@click.option(
    "-b",
    "--build-dir",
    default="build",
    type=click.Path(path_type=pathlib.Path),
    help="Path to build directory",
)
@click.option(
    "-s",
    "--source-dir",
    default="src",
    type=click.Path(path_type=pathlib.Path),
    help="Path to source directory",
)
@click.option(
    "-a",
    "--always-execute",
    is_flag=True,
    help="Always execute tasks, even if up-to-date",
)
@click.option(
    "-n",
    "--num-processes",
    default=os.cpu_count(),
    type=int,
    help="Number of parallel processes to use",
)
@click.option("-v", "--verbose", is_flag=True, help="Enable verbose output")
@click.option("--no-cache", is_flag=True, help="Disable caching mechanism")
@click.option(
    "-c", "--clean", is_flag=True, help="Remove build directory before building"
)
def main(
    dist_dir,
    build_dir,
    params,
    source_dir,
    always_execute,
    num_processes,
    verbose,
    no_cache,
    clean,
    change_dir,
):
    click.echo("Generating configuration ...")

    if change_dir:
        os.chdir(change_dir)

    script_dir = pathlib.Path(__file__).parent

    # Load config defaults
    with open(script_dir / "extras" / "defaults.yaml", "r") as f:
        config_data = yaml.safe_load(f)

    lc = locale.getlocale()[0].split("_")[0]
    locale_file = script_dir / f"defaults_{lc}.yaml"
    if locale_file.exists():
        with open(locale_file, "r") as f:
            config_data = deep_update(config_data, yaml.safe_load(f))

    # Load configuration file if provided
    config_file = source_dir / "config.yaml"
    if config_file.is_file():
        config_data = deep_update(config_data, yaml.safe_load(config_file.read_text()))

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

    click.echo("Generating tasks ...")

    if no_cache:
        cache = {}
    else:
        cache = Cache(pathlib.Path.home() / ".mkmapdiary" / "cache.sqlite")

    if clean and build_dir.is_dir() and (build_dir / "mkdocs.yml").is_file():
        import shutil

        shutil.rmtree(build_dir)

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
    exitcode = DoitMain(ModuleTaskLoader(taskList.toDict())).run(proccess_args)
    click.echo("Done.")
    sys.exit(exitcode)


if __name__ == "__main__":
    main()
