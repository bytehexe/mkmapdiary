from wcwidth import wcswidth
import logging
import logging.config
import contextvars
import pathlib
import yaml


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


def setup_logging(build_dir: pathlib.Path):
    with open(pathlib.Path(__file__).parent.parent / "resources" / "logging.yaml") as f:
        logging_config = yaml.safe_load(f)

    build_dir.mkdir(parents=True, exist_ok=True)
    logging_config["handlers"]["file"]["filename"] = str(build_dir / "mkmapdiary.log")
    logging.config.dictConfig(logging_config)
    console_handler = logging.getHandlerByName("console")
    if console_handler:
        console_handler.addFilter(IconFilter())


class ThisMayTakeAWhile:
    def __init__(self, logger: logging.Logger):
        self.logger = logger

    def __enter__(self):
        self.logger.info("This may take a while ...", extra={"icon": "⏳"})

    def __exit__(self, exc_type, exc_value, traceback):
        self.logger.info("Done.", extra={"icon": "⌛"})
