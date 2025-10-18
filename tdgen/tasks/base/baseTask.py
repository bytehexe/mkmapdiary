import datetime
from collections import namedtuple
from abc import ABC, abstractmethod
from jinja2 import Environment, PackageLoader, select_autoescape, StrictUndefined
import dateutil.parser

class BaseTask(ABC):
    Asset = namedtuple("Asset", ["path", "type", "meta"])

    def __init__(self):
        super().__init__()
        self.__unique_paths = {}

        self.__template_env = Environment(
            loader=PackageLoader("tdgen"),
            autoescape=select_autoescape(),
            undefined=StrictUndefined
        )

    @abstractmethod
    def handle(self, source):
        """Handle a source file or directory based on its tags."""
        pass

    def extract_meta_datetime(self, source):
        """Extract metadata from the file's modification time."""
        
        # If the file does not exist, return None
        try:
            stat = source.stat()
        except FileNotFoundError:
            return None
        
        # Try to extract timestamp from filename
        try:
            return dateutil.parser.parse(source.name, fuzzy=True, ignoretz=True)
        except dateutil.parser.ParserError:
            pass # Ignore and fallback to mtime

        # Fallback: Use the file's modification time
        return datetime.datetime.fromtimestamp(stat.st_mtime)
    
    def template(self, template, **params):
        template = self.__template_env.get_template(template)
        return template.render(**params)
    
    def make_unique_filename(self, source, destination):
        """Generate a unique filename by appending a counter if necessary."""
        candidate = destination
        
        base_path = destination.with_suffix('')
        suffix = destination.suffix

        counter = 1
        while candidate in self.__unique_paths:
            if source == self.__unique_paths[candidate]:
                break

            candidate = base_path.with_name(f"{base_path.stem}_{counter}").with_suffix(suffix)
            counter += 1

        self.__unique_paths[candidate] = source
        return candidate