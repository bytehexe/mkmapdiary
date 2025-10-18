from identify import identify
from collections import namedtuple, defaultdict

from .tasks import ImageTask
from .tasks import SiteTask
from .tasks import Cr2Task
from .tasks import DayPageTask
from .tasks import GeojsonTask
from .tasks import GalleryTask
from .tasks import JournalTask
from .tasks import TextTask
from .tasks import MarkdownTask
from .tasks import AudioTask

from .db import Db

tasks = [
    ImageTask,
    SiteTask,
    Cr2Task,
    DayPageTask,
    GeojsonTask,
    GalleryTask,
    JournalTask,
    TextTask,
    MarkdownTask,
    AudioTask,
]

class TaskList(*tasks):
    """
    Generates task lists based on source directory and configuration.
    
    The TaskList identifies files and directories based on tags and lists
    them accordingly.
    """

    def __init__(self, config, source_dir, build_dir, dist_dir, cache):
        super().__init__()

        self.__config = config
        self.__source_dir = source_dir
        self.__build_dir = build_dir
        self.__files_dir = self.build_dir / "files"
        self.__docs_dir = self.build_dir / "docs"
        self.__templates_dir = self.docs_dir / "templates"
        self.__assets_dir = self.docs_dir / "assets"
        self.__dist_dir = dist_dir
        self.__cache = cache

        # Store assets by date and then type
        self.__db = Db()
        self.__scan()

    @property
    def config(self):
        """Property to access the configuration."""
        return self.__config
    
    @property
    def db(self):
        """Property to access the database."""
        return self.__db
    
    @property
    def source_dir(self):
        """Property to access the source directory."""
        return self.__source_dir
    
    @property
    def build_dir(self):
        """Property to access the build directory."""
        return self.__build_dir
    
    @property
    def files_dir(self):
        """Property to access the files directory."""
        return self.__files_dir
    
    @property
    def docs_dir(self):
        """Property to access the docs directory."""
        return self.__docs_dir
    
    @property
    def templates_dir(self):
        """Property to access the templates directory."""
        return self.__templates_dir
    
    @property
    def assets_dir(self):
        """Property to access the assets directory."""
        return self.__assets_dir
    
    @property
    def dist_dir(self):
        """Property to access the distribution directory."""
        return self.__dist_dir
    
    @property
    def cache(self):
        """Property to access the cache."""
        return self.__cache

    def toDict(self):
        """Convert this object to a dictionary so that doit can use it."""
        return dict((name, getattr(self, name)) for name in dir(self))

    def __scan(self):
        """Scan the source directory and identify files and directories."""
        self.handle(self.source_dir)            

    def handle(self, source):
        """Handle a source file or directory based on its tags."""

        if source.is_file() and source.name == "config.yaml":
            return

        tags = identify.tags_from_path(source)
        print(f"> Processing {source} [{" ".join(tags)}]")

        if not tags:
            print(f"Warning: No tags for {source}")
            return

        handler = None
        for tag in tags:
            try:
                handler = getattr(self, f"handle_{tag.replace('-', '_')}")
                break
            except AttributeError:
                continue

        if handler is not None:
            self.add_assets(handler(source))
            return
        
        ext = ("_".join(x[1:] for x in source.suffixes)).lower()
        try:
            handler = getattr(self, f"handle_ext_{ext}")
        except AttributeError:
            pass

        if handler is not None:
            self.add_assets(handler(source))
            return

        print(f"Warning: No handler for {source} with tags {tags} and extension '{ext}'")            

    def handle_directory(self, source):
        """Handle a directory by processing its contents."""
        for item in source.iterdir():
            self.handle(item)
    
    def handle_symlink(self, source):
        """Handle a symlink by resolving its target."""
        target = source.resolve()
        self.handle(target)
    
    def add_assets(self, assets):
        """Add an asset to the list."""
        if assets is None:
            return
        
        for asset in assets:
            self.db.add_asset(asset.path, asset.type, asset.meta)