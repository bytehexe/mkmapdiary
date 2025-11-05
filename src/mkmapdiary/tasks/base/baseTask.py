import datetime
import threading
from abc import ABC, ABCMeta, abstractmethod
from collections.abc import Callable, Mapping
from pathlib import PosixPath
from typing import Any

import dateutil.parser
import ollama
import whenever
from jinja2 import Environment, PackageLoader, StrictUndefined, select_autoescape

from mkmapdiary.lib.assetRegistry import AssetRegistry
from mkmapdiary.lib.calibration import Calibration
from mkmapdiary.lib.dirs import Dirs
from mkmapdiary.util.cache import with_cache

ai_lock = threading.Lock()


def debug(func: Callable[..., Any]) -> Callable[..., Any]:
    """Decorator to print debug information for a function."""

    def wrapper(*args: Any, **kwargs: Any) -> Any:
        print(f"DEBUG: Calling {func.__name__} with args={args}, kwargs={kwargs}")
        result = func(*args, **kwargs)
        print(
            f"DEBUG: Called {func.__name__} with args={args}, kwargs={kwargs}, returned {result}",
        )
        return result

    return wrapper


class BaseTask(ABC, metaclass=ABCMeta):
    def __init__(self) -> None:
        super().__init__()
        self.__unique_paths: dict[PosixPath, PosixPath] = {}

        self.__template_env = Environment(
            loader=PackageLoader("mkmapdiary"),
            autoescape=select_autoescape(),
            undefined=StrictUndefined,
        )

    @abstractmethod
    def handle(self, source: PosixPath) -> Any:
        """Handle a source file or directory based on its tags."""

    @property
    @abstractmethod
    def config(self) -> dict:
        """Property to access the configuration."""

    @property
    @abstractmethod
    def db(self) -> AssetRegistry:
        """Property to access the database."""

    @property
    @abstractmethod
    def dirs(self) -> Dirs:
        """Property to access the directory structure."""

    @property
    @abstractmethod
    def calibration(self) -> Calibration:
        """Property to access the current calibration."""

    @property
    @abstractmethod
    def cache(self) -> Mapping[tuple[str, tuple[Any] | list[Any]], Any]:
        """Property to access the cache."""

    def calibrate(
        self, dt: whenever.PlainDateTime | datetime.datetime
    ) -> whenever.Instant:
        """Calibrate a PlainDateTime to an Instant using the current calibration."""
        calibration = self.calibration
        return self._calibrate(dt, calibration)

    @staticmethod
    def _calibrate(
        dt: whenever.PlainDateTime | datetime.datetime, calibration: Calibration
    ) -> whenever.Instant:
        if isinstance(dt, datetime.datetime):
            dt = whenever.PlainDateTime.from_py_datetime(dt)
        return (
            dt.assume_tz(calibration.timezone)
            .to_instant()
            .subtract(seconds=calibration.offset)
        )

    def extract_meta_datetime(self, source: PosixPath) -> whenever.Instant | None:
        """Extract metadata from the file's modification time."""

        # If the file does not exist, return None
        try:
            stat = source.stat()
        except FileNotFoundError:
            return None

        # Try to extract timestamp from filename
        timestr = "".join(x for x in str(source.stem) if x.isdigit())
        try:
            py_datetime = dateutil.parser.parse(
                f"<{timestr}>", fuzzy=True, ignoretz=True
            )
            calibration = self.calibration
            return (
                whenever.PlainDateTime.from_py_datetime(py_datetime)
                .assume_tz(calibration.timezone)
                .to_instant()
                .add(seconds=calibration.offset)
            )

        except dateutil.parser.ParserError:
            pass  # Ignore and fallback to mtime

        # Fallback: Use the file's modification time
        py_datetime = datetime.datetime.fromtimestamp(stat.st_mtime)
        return (
            whenever.PlainDateTime.from_py_datetime(py_datetime)
            .assume_tz(self.calibration.timezone)
            .to_instant()
            .add(seconds=self.calibration.offset)
        )

    def template(self, template_name: str, **params: Any) -> str:
        template = self.__template_env.get_template(template_name)
        return template.render(**params)

    def make_unique_filename(
        self,
        source: PosixPath,
        destination: PosixPath,
    ) -> PosixPath:
        """Generate a unique filename by appending a counter if necessary."""
        candidate = destination

        base_path = destination.with_suffix("")
        suffix = destination.suffix

        counter = 1
        while candidate in self.__unique_paths:
            if source == self.__unique_paths[candidate]:
                break

            candidate = base_path.with_name(f"{base_path.stem}_{counter}").with_suffix(
                suffix,
            )
            counter += 1

        self.__unique_paths[candidate] = source
        return candidate

    def ai(self, key: str, format_args: dict[str, Any]) -> str:
        return self.__ai(
            self.config["llm_prompts"][key]["prompt"].format(**format_args),
            options=self.config["llm_prompts"][key]["options"],
        )

    def __ai(self, prompt: str, **params: Any) -> str:
        """Generate text using an AI model."""

        model = self.config["features"]["llms"]["text_model"]

        with ai_lock:
            response = ollama.chat(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                **params,
            )

        return response["message"]["content"].strip()

    def with_cache(self, *args: Any, **params: Any) -> Any:
        """Get the value from cache or compute it if not present."""

        return with_cache(self.cache, *args, **params)
