import contextvars
import logging
import logging.config
import pathlib

import yaml
from wcwidth import wcswidth


class IconFilter(logging.Filter):
    def __pad_icon(self, icon: str) -> str:
        width = wcswidth(icon)
        length = len(icon)
        pad = 2 + length - width
        return icon + " " * (pad)

    def filter(self, record):
        if hasattr(record, "icon"):
            record.fmt_icon = self.__pad_icon(record.icon)
        else:
            if record.levelno >= logging.ERROR:
                record.fmt_icon = self.__pad_icon("💥")
            elif record.levelno >= logging.WARNING:
                record.fmt_icon = self.__pad_icon("⚠️")
        return True


class StepFilter(logging.Filter):
    def filter(self, record):
        if record.name == "mkmapdiary.main.runner":
            return True
        if record.name == "mkmapdiary.taskList":
            return True
        if hasattr(record, "is_step") and record.is_step:
            return True
        if record.levelno >= logging.WARNING:
            return True
        return False


def record_factory(*args, **kwargs):
    record = old_factory(*args, **kwargs)
    record.task = current_task.get()
    return record


old_factory = logging.getLogRecordFactory()
logging.setLogRecordFactory(record_factory)

current_task = contextvars.ContextVar("current_task", default="unknown")


def setup_logging():
    """Setup console logging configuration."""
    with open(pathlib.Path(__file__).parent.parent / "resources" / "logging.yaml") as f:
        logging_config = yaml.safe_load(f)

    logging.config.dictConfig(logging_config)
    console_handler = logging.getHandlerByName("console")
    if console_handler:
        console_handler.addFilter(IconFilter())


def add_file_logging(build_dir: pathlib.Path):
    """Add file logging to existing logging setup.

    Args:
        build_dir: Directory where the log file should be created.
    """
    build_dir.mkdir(parents=True, exist_ok=True)
    log_file = build_dir / "mkmapdiary.log"

    # Create file handler
    file_handler = logging.FileHandler(str(log_file), mode="w")
    file_handler.setLevel(logging.DEBUG)

    # Set formatter
    formatter = logging.Formatter(
        "%(asctime)s: %(name)s, %(task)s [%(levelname)s] %(message)s",
    )
    file_handler.setFormatter(formatter)

    # Add to root logger
    root_logger = logging.getLogger()
    root_logger.addHandler(file_handler)


class ThisMayTakeAWhile:
    def __init__(self, logger: logging.Logger, info=None):
        self.logger = logger
        self.__info = info

    def __enter__(self):
        if self.__info:
            text = f"{self.__info} - This may take a while ..."
        else:
            text = "This may take a while ..."
        self.logger.info(text, extra={"icon": "⏳"})

    def __exit__(self, exc_type, exc_value, traceback):
        if self.__info:
            text = f" {self.__info[0].lower()}{self.__info[1:]}"
        else:
            text = ""
        self.logger.info(f"Done{text}.", extra={"icon": "⌛"})
