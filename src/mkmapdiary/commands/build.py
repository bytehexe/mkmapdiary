import gettext
import locale
import logging
import os
import pathlib
import sys
import tempfile

import click
import doit.reporter
from doit.cmd_base import ModuleTaskLoader
from doit.doit_cmd import DoitMain
from jsonschema.exceptions import ValidationError
from tabulate import tabulate

from .. import util
from ..cache import Cache
from ..lib.config import load_config_file, load_config_param
from ..lib.dirs import Dirs
from ..taskList import TaskList
from ..util.log import add_file_logging, current_task

logger = logging.getLogger(__name__)
runner_logger = logging.getLogger(__name__ + ".runner")


def main(
    dist_dir,
    build_dir,
    params,
    source_dir,
    always_execute,
    num_processes,
    verbose,
    quiet,
    no_cache,
):
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

    # Load config defaults
    default_config = dirs.resources_dir / "defaults.yaml"
    try:
        config_data = load_config_file(default_config)
    except ValidationError as e:
        logger.critical(f"Default configuration is invalid: {e.message}")
        logger.info(f"Path: {'.'.join(str(p) for p in e.path)}")
        sys.exit(1)
    except ValueError as e:
        logger.critical(f"Error loading default configuration: {e}")
        sys.exit(1)

    # Load local user configuration
    user_config_file = dirs.user_config_file
    if user_config_file.exists():
        try:
            config_data = util.deep_update(
                config_data, load_config_file(user_config_file)
            )
        except ValidationError as e:
            logger.error(f"User configuration is invalid: {e.message}")
            logger.info(f"Path: {'.'.join(str(p) for p in e.path)}")
            sys.exit(1)
        except ValueError as e:
            logger.error(f"Error loading user configuration: {e}")
            sys.exit(1)

    # Load project configuration file if provided
    project_config_file = dirs.source_dir / "config.yaml"
    if project_config_file.is_file():
        try:
            config_data = util.deep_update(
                config_data, load_config_file(project_config_file)
            )
        except ValidationError as e:
            logger.error(f"Project configuration is invalid: {e.message}")
            logger.info(f"Path: {'.'.join(str(p) for p in e.path)}")
            sys.exit(1)
        except ValueError as e:
            logger.error(f"Error loading project configuration: {e}")
            sys.exit(1)

    # Override config with params
    for param in params:
        try:
            param_config = load_config_param(param)
            config_data = util.deep_update(config_data, param_config)
        except ValidationError as e:
            logger.error(f"Config parameter '{param}' is invalid: {e.message}")
            logger.info(f"Path: {'.'.join(str(p) for p in e.path)}")
            sys.exit(1)
        except ValueError as e:
            logger.error(f"Error loading config parameter '{param}': {e}")
            sys.exit(1)

    # Load gettext
    localedir = dirs.locale_dir

    language = config_data["site"]["locale"].split("_")[0]

    lang = gettext.translation(
        "messages",
        localedir=str(localedir),
        languages=[language],
        fallback=False,
    )
    lang.install()
    _ = lang.gettext

    # Load translations
    for key, value in config_data["strings"].items():
        if value is None:
            translation = _(key)
            config_data["strings"][key] = translation

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
                "Error: Transcription feature requires the 'whisper' package to be installed."
            )
            sys.exit(1)

    logger.info("Preparing directories ...")
    # Sanity checks
    if not source_dir.is_dir():
        logger.error(
            f"Error: Source directory '{source_dir}' does not exist or is not a directory."
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
            f"Error: Build directory '{build_dir}' is not empty and does not contain a .mkmapdiary_build_dir file."
        )
        sys.exit(1)
    if (
        dist_dir.is_dir()
        and any(dist_dir.iterdir())
        and not (dist_dir / "index.html").is_file()
    ):
        logger.error(
            f"Error: Distribution directory '{dist_dir}' is not empty and does not contain an index.html file."
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
            build_dir, keep_files=["mkmapdiary.log", ".mkmapdiary_build_dir"]
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
    taskList = TaskList(config_data, dirs, cache)

    n_assets = taskList.db.count_assets()

    if n_assets > 0:
        asset_str = tabulate(*taskList.db.dump())
    else:
        asset_str = ""
    logger.debug(
        f"Found {n_assets} assets" + (f":\n{asset_str}" if n_assets > 0 else ".")
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
        def execute_task(self, task):
            display_name = task.name
            if "/" in display_name:
                display_name = (
                    display_name.split(":")[0] + ":.../" + display_name.split("/")[-1]
                )
            current_task.set(display_name)
            super().execute_task(task)

        def write(self, text):
            runner_logger.info(text.rstrip())

    doit_config = {
        "GLOBAL": {
            "backend": "sqlite3",
            "dep_file": str(dirs.doit_db_path),
            "reporter": CustomReporter,
        }
    }
    exitcode = DoitMain(
        ModuleTaskLoader(taskList.toDict()),
        config_filenames=(),
        extra_config=doit_config,
    ).run(proccess_args)
    logger.info("Done.", extra={"icon": "✅"})
    sys.exit(exitcode)


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
@click.option(
    "--no-cache",
    is_flag=True,
    help="Disable cache in the home directory (not recommended)",
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
    ctx,
    source_dir,
    dist_dir,
    build_dir,
    persistent_build,
    params,
    always_execute,
    num_processes,
    no_cache,
):
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

    def main_exec():
        main(
            dist_dir=dist_dir,
            build_dir=build_dir,
            source_dir=source_dir,
            params=params,
            always_execute=always_execute,
            num_processes=num_processes,
            verbose=verbose,
            quiet=quiet,
            no_cache=no_cache,
        )

    if build_dir is None:
        with tempfile.TemporaryDirectory() as tmpdirname:
            build_dir = pathlib.Path(tmpdirname)
            main_exec()
    else:
        main_exec()
