import datetime
from collections import namedtuple
from abc import ABC, abstractmethod

class BaseTask(ABC):
    Asset = namedtuple("Asset", ["path", "type", "meta"])

    @abstractmethod
    def handle(self, source):
        """Handle a source file or directory based on its tags."""
        pass

    def extract_meta_mtime(self, source):
        """Extract metadata from the file's modification time."""
        stat = source.stat()
        return datetime.datetime.fromtimestamp(stat.st_mtime)