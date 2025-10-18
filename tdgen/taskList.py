from identify import identify
from collections import namedtuple, defaultdict

from .tasks import ImageTask
from .tasks import SiteTask
from .tasks import Cr2Task

Asset = namedtuple("Asset", ["path", "type", "metadata"])

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
        self.dist_dir = dist_dir
        self.assets_dir = self.dist_dir / "site" / "assets"
        self.scan()

    def toDict(self):
        return dict((name, getattr(self, name)) for name in dir(self))

    def scan(self):
        self.handle(self.source_dir)            

    def handle(self, source):
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
            handler(source)
            return
        
        ext = source.suffix.lower()[1:]
        try:
            handler = getattr(self, f"handle_ext_{ext}")
        except AttributeError:
            pass

        if handler is not None:
            handler(source)
            return

        print(f"Warning: No handler for {source} with tags {tags} and extension '{ext}'")            

    def handle_directory(self, source):
        for item in source.iterdir():
            self.handle(item)
    
    def handle_symlink(self, source):
        target = source.resolve()
        self.handle(target)