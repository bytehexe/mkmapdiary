from identify import identify
from collections import namedtuple, defaultdict

from .tasks import ImageTask
from .tasks import SiteTask
from .tasks import Cr2Task
from .db import Db

class TaskList(ImageTask, SiteTask, Cr2Task):
    """
    Generates task lists based on source directory and configuration.
    
    The TaskList identifies files and directories based on tags and lists
    them accordingly.
    """

    def __init__(self, config, source_dir, build_dir, dist_dir):
        super().__init__()

        self.config = config
        self.source_dir = source_dir
        self.build_dir = build_dir
        self.files_dir = self.build_dir / "files"
        self.docs_dir = self.build_dir / "docs"
        self.assets_dir = self.docs_dir / "assets"
        self.dist_dir = dist_dir

        # Store assets by date and then type
        self.db = Db()
        self.__scan()

    def toDict(self):
        """Convert this object to a dictionary so that doit can use it."""
        return dict((name, getattr(self, name)) for name in dir(self))

    def __scan(self):
        """Scan the source directory and identify files and directories."""
        self.handle(self.source_dir)            

    def handle(self, source):
        """Handle a source file or directory based on its tags."""
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
            self.add_asset(handler(source))
            return
        
        ext = source.suffix.lower()[1:]
        try:
            handler = getattr(self, f"handle_ext_{ext}")
        except AttributeError:
            pass

        if handler is not None:
            self.add_asset(handler(source))
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
    
    def add_asset(self, asset):
        """Add an asset to the list."""
        if asset is None:
            return

        self.db.add_asset(asset.path, asset.type, asset.meta)