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
import logging.config
import doit.reporter
import contextvars
import sys


def record_factory(*args, **kwargs):
    record = old_factory(*args, **kwargs)
    record.task = current_task.get()
    return record


old_factory = logging.getLogRecordFactory()
logging.setLogRecordFactory(record_factory)

logger = logging.getLogger(__name__)
current_task = contextvars.ContextVar("current_task", default="unknown")


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
    # Set up logging
    with open(pathlib.Path(__file__).parent / "resources" / "logging.yaml") as f:
        logging_config = yaml.safe_load(f)

    build_dir.mkdir(parents=True, exist_ok=True)
    logging_config["handlers"]["file"]["filename"] = str(build_dir / "mkmapdiary.log")
    logging.config.dictConfig(logging_config)

    logger.info("Starting mkmapdiary")
    log = build_dir / "mkmapdiary.log"
    logger.info(f"Build dir: {log}")

    logger.info("Generating configuration ...")

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
        util.clean_dir(build_dir)

    logger.info("Generating tasks ...")

    if no_cache:
        cache = {}
    else:
        cache = Cache(pathlib.Path.home() / ".mkmapdiary" / "cache.sqlite")

    taskList = TaskList(config_data, source_dir, build_dir, dist_dir, cache)

    n_assets = taskList.db.count_assets()
    logger.info(f"Found {n_assets} assets" + (":" if n_assets > 0 else "."))
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

    logger.info("Running tasks ...")

    class CustomReporter(doit.reporter.ConsoleReporter):
        def execute_task(self, task):
            display_name = task.name
            if len(display_name) > 30:
                if "/" in display_name:
                    display_name_front = display_name.split(":", 1)[0]
                    display_name_back = display_name[-26 + len(display_name_front) :]
                    display_name = f"{display_name_front}:...{display_name_back}"
                else:
                    display_name = display_name[:27] + "..."
            current_task.set(display_name)
            super().execute_task(task)
            current_task.set("unknown")

        def write(self, text):
            logger.info(text.rstrip())

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
    logger.info("Done.")
    sys.exit(exitcode)
