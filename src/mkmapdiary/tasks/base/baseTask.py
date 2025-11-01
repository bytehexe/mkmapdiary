import datetime
import threading
from abc import ABC, abstractmethod
from pathlib import PosixPath
from typing import Any, List, Mapping, Optional, Tuple, Union

import dateutil.parser
import ollama
from jinja2 import Environment, PackageLoader, StrictUndefined, select_autoescape

from mkmapdiary.db import Db
from mkmapdiary.lib.dirs import Dirs
from mkmapdiary.util.cache import with_cache

ai_lock = threading.Lock()


def debug(func):
    """Decorator to print debug information for a function."""

    def wrapper(*args, **kwargs):
        print(f"DEBUG: Calling {func.__name__} with args={args}, kwargs={kwargs}")
        result = func(*args, **kwargs)
        print(
            f"DEBUG: Called {func.__name__} with args={args}, kwargs={kwargs}, returned {result}",
        )
        return result

    return wrapper


class BaseTask(ABC):
    def __init__(self) -> None:
        super().__init__()
        self.__unique_paths: dict[PosixPath, PosixPath] = {}

        self.__template_env = Environment(
            loader=PackageLoader("mkmapdiary"),
            autoescape=select_autoescape(),
            undefined=StrictUndefined,
        )

    @abstractmethod
    def handle(self, source):
        """Handle a source file or directory based on its tags."""

    @property
    @abstractmethod
    def config(self) -> dict:
        """Property to access the configuration."""

    @property
    @abstractmethod
    def db(self) -> Db:
        """Property to access the database."""

    @property
    @abstractmethod
    def dirs(self) -> Dirs:
        """Property to access the directory structure."""

    @property
    @abstractmethod
    def cache(self) -> Mapping[Tuple[str, Union[Tuple[Any], List[Any]]], Any]:
        """Property to access the cache."""

    def extract_meta_datetime(self, source: PosixPath) -> Optional[datetime.datetime]:
        """Extract metadata from the file's modification time."""

        # If the file does not exist, return None
        try:
            stat = source.stat()
        except FileNotFoundError:
            return None

        # Try to extract timestamp from filename
        timestr = "".join(x for x in str(source.stem) if x.isdigit())
        try:
            return dateutil.parser.parse(f"<{timestr}>", fuzzy=True, ignoretz=True)
        except dateutil.parser.ParserError:
            pass  # Ignore and fallback to mtime

        # Fallback: Use the file's modification time
        return datetime.datetime.fromtimestamp(stat.st_mtime)

    def template(self, template, **params) -> str:
        template = self.__template_env.get_template(template)
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

    def ai(self, key, format_args) -> str:
        return self.__ai(
            self.config["llm_prompts"][key]["prompt"].format(**format_args),
            options=self.config["llm_prompts"][key]["options"],
        )

    def __ai(self, prompt, **params) -> str:
        """Generate text using an AI model."""

        model = self.config["features"]["llms"]["text_model"]

        with ai_lock:
            response = ollama.chat(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                **params,
            )

        return response["message"]["content"].strip()

    def with_cache(self, *args, **params) -> Any:
        """Get the value from cache or compute it if not present."""

        return with_cache(self.cache, *args, **params)
