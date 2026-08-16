import locale
import logging
import os
import pathlib
import queue
import sys
import tempfile
from collections.abc import MutableMapping
from contextlib import nullcontext
from typing import Any

import click
import doit.reporter
import doit.task
import poiidx
import yaml
from doit.cmd_base import ModuleTaskLoader
from doit.doit_cmd import DoitMain
from tabulate import tabulate

from .. import util
from ..lib.cache import Cache
from ..lib.config import install_translations, resolve_config
from ..lib.dirs import Dirs
from ..taskList import TaskList
from ..util.log import add_file_logging, current_task
from .params import params_option

logger = logging.getLogger(__name__)
runner_logger = logging.getLogger(__name__ + ".runner")


def main(
    dist_dir: pathlib.Path,
    build_dir: pathlib.Path,
    params: tuple[str, ...],
    source_dir: pathlib.Path,
    always_execute: bool,
    num_processes: int,
    verbose: bool,
    quiet: bool,
    no_cache: bool,
    profile: bool,
    debug_fast: bool,
) -> None:
    # Add file logging for build command (console logging already configured at CLI level)
    add_file_logging(build_dir)

    current_task.set("main")

    if not source_dir:
        raise click.BadParameter("Source directory is required.")

    dirs = Dirs(source_dir, build_dir, dist_dir, create_dirs=False)

    logger.info("Starting mkmapdiary")
    log = dirs.log_file_path
    logger.debug(f"Log: {log}", extra={"icon": "📄"})

    logger.info("Generating configuration ...", extra={"icon": "⚙️"})

    config_data: MutableMapping[str, Any] = resolve_config(dirs, params, debug_fast)

    # Load gettext and the translations for the configured strings
    lang = install_translations(config_data, dirs.locale_dir)

    # Set locale
    logger.debug(f"Setting locale to {config_data['site']['locale']}")
    locale.setlocale(locale.LC_TIME, config_data["site"]["locale"])

    # Feature checks
    features = config_data["features"]
    if features["transcription"]["enabled"] is True:
        try:
            import whisper  # noqa: F401, I001
        except ImportError:
            logger.error(
                "Error: Transcription feature requires the 'whisper' package to be installed.",
            )
            sys.exit(1)

    if config_data["debug"]["enable_user_cache"]:
        logger.info("User cache is enabled.", extra={"icon": "🗃️"})

    logger.info("Preparing directories ...")
    # Sanity checks
    if not source_dir.is_dir():
        logger.error(
            f"Error: Source directory '{source_dir}' does not exist or is not a directory.",
        )
        sys.exit(1)
    if build_dir.is_file():
        logger.error(f"Error: Build directory '{build_dir}' is a file.")
        sys.exit(1)
    if dist_dir.is_file():
        logger.error(f"Error: Distribution directory '{dist_dir}' is a file.")
        sys.exit(1)
    if build_dir == dist_dir:
        logger.error("Error: Build and distribution directories must be different.")
        sys.exit(1)
    if build_dir == source_dir:
        logger.error("Error: Build and source directories must be different.")
        sys.exit(1)
    if dist_dir == source_dir:
        logger.error("Error: Distribution and source directories must be different.")
        sys.exit(1)
    if (
        build_dir.is_dir()
        and any(x for x in build_dir.iterdir() if x.name != "mkmapdiary.log")
        and not dirs.build_dir_marker_file.is_file()
    ):
        logger.error(
            f"Error: Build directory '{build_dir}' is not empty and does not contain a .mkmapdiary_build_dir file.",
        )
        sys.exit(1)
    if (
        dist_dir.is_dir()
        and any(dist_dir.iterdir())
        and not (dist_dir / "index.html").is_file()
    ):
        logger.error(
            f"Error: Distribution directory '{dist_dir}' is not empty and does not contain an index.html file.",
        )
        sys.exit(1)

    # Create directories
    if not dist_dir.is_dir():
        dist_dir.mkdir(parents=True, exist_ok=True)
    if not build_dir.is_dir():
        build_dir.mkdir(parents=True, exist_ok=True)

    # Create build directory marker file
    dirs.build_dir_marker_file.touch()

    # Clean build directory if needed
    if always_execute:
        util.clean_dir(
            build_dir,
            keep_files=["mkmapdiary.log", ".mkmapdiary_build_dir"],
        )

    logger.info("Generating tasks ...", extra={"icon": "📝", "is_step": True})

    if no_cache:
        # Create a temporary cache that won't persist
        import tempfile

        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as temp_cache:
            cache = Cache(pathlib.Path(temp_cache.name))
    else:
        cache = Cache(dirs.cache_db_path)

    dirs.create_dirs = True
    taskList = TaskList(dict(config_data), dirs, cache, gettext=lang.gettext)

    n_assets = taskList.db.count_assets()

    if n_assets > 0:
        asset_str = tabulate(*taskList.db.dump())
    else:
        asset_str = ""
    logger.debug(
        f"Found {n_assets} assets" + (f":\n{asset_str}" if n_assets > 0 else "."),
    )

    # Check if poi is enabled, if so, initialize poiidx
    if config_data["features"]["poi_detection"]["enabled"]:
        logger.info("Initializing POI index ...", extra={"icon": "🗺️"})
        filter_config_file = dirs.resources_dir / "poi_filter_config.yaml"
        with open(filter_config_file) as f:
            filter_config = yaml.safe_load(f)

        poiidx.init(
            filter_config=filter_config,
            database=config_data["features"]["poi_detection"]["connection"]["database"],
            host=config_data["features"]["poi_detection"]["connection"]["host"],
            user=config_data["features"]["poi_detection"]["connection"]["user"],
            password=config_data["features"]["poi_detection"]["connection"]["password"],
        )

    proccess_args = []
    if always_execute:
        proccess_args.append("--always-execute")
    if num_processes > 0:
        proccess_args.append(f"--process={num_processes}")
    if verbose:
        proccess_args.extend(["-v", "2"])
    proccess_args.append("--parallel-type=thread")

    logger.info("Running tasks ...", extra={"icon": "🚀", "is_step": True})

    class CustomReporter(doit.reporter.ConsoleReporter):
        def execute_task(self, task: doit.task.Task) -> None:
            display_name = task.name
            if "/" in display_name:
                display_name = (
                    display_name.split(":")[0] + ":.../" + display_name.split("/")[-1]
                )
            current_task.set(display_name)
            super().execute_task(task)

        def write(self, text: str) -> None:
            runner_logger.info(text.rstrip())

    doit_config = {
        "GLOBAL": {
            "backend": "sqlite3",
            "dep_file": str(dirs.doit_db_path),
            "reporter": CustomReporter,
        },
    }
    exitcode = DoitMain(
        ModuleTaskLoader(taskList.toDict()),
        config_filenames=(),
        extra_config=doit_config,
    ).run(proccess_args)
    if exitcode == 0:
        logger.info("Done.", extra={"icon": "✅"})
    else:
        logger.error(
            f"Error: Build failed (exit code {exitcode}), see the task output above.",
        )

    if profile:
        import yappi
        from doit.runner import MThreadRunner

        yappi.get_func_stats(
            filter_callback=lambda stat: not yappi.module_matches(stat, [queue])
            and not yappi.func_matches(stat, [MThreadRunner.execute_task_subprocess]),
        ).save("mkmapdiary_profile.prof", type="pstat")
        logger.info(
            "Profile data saved to mkmapdiary_profile.prof",
            extra={"icon": "📊"},
        )

    sys.exit(exitcode)


@click.command()
@params_option
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
@click.option(
    "--no-cache",
    is_flag=True,
    help="Disable cache in the home directory (not recommended)",
)
@click.option(
    "--profile",
    is_flag=True,
    help="Enable profiling of the build process",
)
@click.option(
    "--debug-fast",
    is_flag=True,
    help="Enable fast debug mode (for development purposes only). This disables slow features or uses faster alternatives.",
)
@click.argument(
    "source_dir",
    type=click.Path(path_type=pathlib.Path),
    required=True,
)
@click.argument(
    "dist_dir",
    type=click.Path(path_type=pathlib.Path),
    required=False,
)
@click.pass_context
def build(
    ctx: click.Context,
    source_dir: pathlib.Path,
    dist_dir: pathlib.Path | None,
    build_dir: pathlib.Path | None,
    persistent_build: bool,
    params: tuple[str, ...],
    always_execute: bool,
    num_processes: int,
    no_cache: bool,
    profile: bool,
    debug_fast: bool,
) -> None:
    """Build the map diary from source directory to distribution directory."""
    # Get verbosity settings from CLI group context
    verbose = ctx.obj["verbose"]
    quiet = ctx.obj["quiet"]

    # Do not add tasks here, only adjust directories and call main()
    # Main reason: Logging setup needs to happen before any tasks are run

    if dist_dir is None:
        dist_dir = source_dir.with_name(source_dir.name + "_dist")

    if persistent_build and build_dir is None:
        build_dir = source_dir.with_name(source_dir.name + "_build")

    if profile:
        import yappi

        yappi.set_clock_type("wall")
        profile_context = yappi.run()
    else:
        profile_context = nullcontext()

    build_dir_context: Any
    if build_dir is None:
        build_dir_context = tempfile.TemporaryDirectory()
    else:
        build_dir_context = nullcontext(build_dir)

    with build_dir_context as tmpdirname, profile_context:
        temp_build_dir = pathlib.Path(tmpdirname)
        main(
            dist_dir=dist_dir,
            build_dir=temp_build_dir,
            source_dir=source_dir,
            params=params,
            always_execute=always_execute,
            num_processes=num_processes,
            verbose=verbose,
            quiet=quiet,
            no_cache=no_cache,
            profile=profile,
            debug_fast=debug_fast,
        )
    # Note: main() will call sys.exit()
