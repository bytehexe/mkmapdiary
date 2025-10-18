import datetime
from collections import namedtuple
from abc import ABC, abstractmethod
from jinja2 import Environment, PackageLoader, select_autoescape, StrictUndefined
import dateutil.parser
import ollama
import threading
from pathlib import PosixPath
from typing import Optional

ai_lock = threading.Lock()


def debug(func):
    """Decorator to print debug information for a function."""

    def wrapper(*args, **kwargs):
        print(f"DEBUG: Calling {func.__name__} with args={args}, kwargs={kwargs}")
        result = func(*args, **kwargs)
        print(
            f"DEBUG: Called {func.__name__} with args={args}, kwargs={kwargs}, returned {result}"
        )
        return result

    return wrapper


class BaseTask(ABC):
    Asset = namedtuple("Asset", ["path", "type", "meta"])

    def __init__(self):
        super().__init__()
        self.__unique_paths = {}

        self.__template_env = Environment(
            loader=PackageLoader("mkmapdiary"),
            autoescape=select_autoescape(),
            undefined=StrictUndefined,
        )

    @abstractmethod
    def handle(self, source):
        """Handle a source file or directory based on its tags."""
        pass

    @property
    @abstractmethod
    def config(self):
        """Property to access the configuration."""

    @property
    @abstractmethod
    def db(self):
        """Property to access the database."""

    @property
    @abstractmethod
    def source_dir(self):
        """Property to access the source directory."""

    @property
    @abstractmethod
    def build_dir(self):
        """Property to access the build directory."""

    @property
    @abstractmethod
    def files_dir(self):
        """Property to access the files directory."""

    @property
    @abstractmethod
    def docs_dir(self):
        """Property to access the docs directory."""

    @property
    @abstractmethod
    def templates_dir(self):
        """Property to access the templates directory."""

    @property
    @abstractmethod
    def assets_dir(self):
        """Property to access the assets directory."""

    @property
    @abstractmethod
    def dist_dir(self):
        """Property to access the distribution directory."""

    @property
    @abstractmethod
    def cache(self):
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

    def template(self, template, **params):
        template = self.__template_env.get_template(template)
        return template.render(**params)

    def make_unique_filename(
        self, source: PosixPath, destination: PosixPath
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
                suffix
            )
            counter += 1

        self.__unique_paths[candidate] = source
        return candidate

    def ai(self, key, format):
        return self.__ai(
            self.config["ai"][key]["prompt"].format(**format),
            options=self.config["ai"][key]["options"],
        )

    def __ai(self, prompt, **params):
        """Generate text using an AI model."""

        model = self.config["ollama_ai_model"]

        with ai_lock:
            response = ollama.chat(
                model=model, messages=[{"role": "user", "content": prompt}], **params
            )

        return response["message"]["content"].strip()

    def with_cache(self, key, compute_func, *args, cache_args=None):
        """Get the value from cache or compute it if not present."""

        assert type(key) is str, "Key must be a string"
        assert callable(compute_func), "compute_func must be callable"

        if cache_args is None:
            full_key = (key, args)
        else:
            full_key = (key, cache_args)

        try:
            return self.cache[full_key]
        except KeyError:
            value = compute_func(*args)
            self.cache[full_key] = value
            return value
