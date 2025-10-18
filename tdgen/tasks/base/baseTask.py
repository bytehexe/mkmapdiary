import datetime
from collections import namedtuple
from abc import ABC, abstractmethod

class BaseTask(ABC):
    Asset = namedtuple("Asset", ["path", "type", "meta"])

    def __init__(self):
        super().__init__()
        self.__unique_paths = {}

    @abstractmethod
    def handle(self, source):
        """Handle a source file or directory based on its tags."""
        pass

    def extract_meta_mtime(self, source):
        """Extract metadata from the file's modification time."""
        try:
            stat = source.stat()
        except FileNotFoundError:
            return None
        return datetime.datetime.fromtimestamp(stat.st_mtime)
    
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