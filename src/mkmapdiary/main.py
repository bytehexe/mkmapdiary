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
import locale
import gettext
import logging
import doit.reporter
import sys
from mkmapdiary.util.log import setup_logging, current_task, StepFilter

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
    setup_logging(build_dir)

    if verbose > 0 and quiet > 0:
        logger.error("Error: Cannot use both verbose and quiet options together.")
        sys.exit(1)

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

    current_task.set("main")

    logger.info("Starting mkmapdiary")
    log = build_dir / "mkmapdiary.log"
    logger.debug(f"Log: {log}", extra={"icon": "📄"})

    logger.info("Generating configuration ...", extra={"icon": "⚙️"})

    script_dir = pathlib.Path(__file__).parent

    # Load config defaults
    default_config = script_dir / "resources" / "defaults.yaml"
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
    if config_data["locale"] == "C":
        language = "en"
    else:
        language = config_data["locale"].split("_")[0]
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
        and any(build_dir.iterdir())
        and not (build_dir / "mkmapdiary.log").is_file()
    ):
        logger.error(
            f"Error: Build directory '{build_dir}' is not empty and does not contain a mkmapdiary.log file."
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

    # Clean build directory if needed
    if always_execute:
        util.clean_dir(build_dir, keep_files=["mkmapdiary.log"])

    logger.info("Generating tasks ...", extra={"icon": "📝", "is_step": True})

    if no_cache:
        cache = {}
    else:
        cache = Cache(pathlib.Path.home() / ".mkmapdiary" / "cache.sqlite")

    taskList = TaskList(config_data, source_dir, build_dir, dist_dir, cache)

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
            current_task.set("unknown")

        def write(self, text):
            runner_logger.info(text.rstrip())

    doit_config = {
        "GLOBAL": {
            "backend": "sqlite3",
            "dep_file": str(build_dir / "doit.db"),
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
