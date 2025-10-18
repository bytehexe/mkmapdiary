from identify import identify
from collections import namedtuple, defaultdict
from . import tasks

Asset = namedtuple("Asset", ["path", "type", "metadata"])
Context = namedtuple("Context", ["assets"])

class Generator:
    """
    Generates tasks based on source directory and configuration.
    
    The generator identifies files and directories based on tags and processes them accordingly.
    From there, it generates tasks that can be executed to build the desired output.

    """

    def __init__(self, config, source_dir, build_dir, dist_dir):
        self.config = config
        self.source_dir = source_dir
        self.build_dir = build_dir
        self.dist_dir = dist_dir
        self.assets_dir = self.dist_dir / "site" / "assets"

    def __call__(self):
        ctx = Context(assets=defaultdict(list))

        yield from self.generate(self.source_dir, ctx)            
        yield from self.process_assets(ctx)
        yield from self.create_dist(ctx)

    def generate(self, source, ctx):
        tags = identify.tags_from_path(source)
        print(f"Processing {source} [{" ".join(tags)}]")

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
            yield from handler(source, ctx)
            return
        
        ext = source.suffix.lower()[1:]
        try:
            handler = getattr(self, f"handle_ext_{ext}")
        except AttributeError:
            pass

        if handler is not None:
            yield from handler(source, ctx)
            return

        print(f"Warning: No handler for {source} with tags {tags} and extension '{ext}'")            

    def handle_directory(self, source, ctx):
        for item in source.iterdir():
            yield from self.generate(item, ctx)
    
    def handle_symlink(self, source, ctx):
        target = source.resolve()
        yield from self.generate(target, ctx)

    def handle_image(self, source, ctx):
        # Create task to convert image to target format
        format = self.config.get("image_format", "jpeg")
        yield tasks.convert_image(source, (self.assets_dir / source.stem).with_suffix(f".{format}"), format=format)

    def handle_ext_cr2(self, source, ctx):
        intermediate_file = (self.build_dir / source.stem).with_suffix(".jpeg")
        yield tasks.convert_raw(source, intermediate_file)

        format = self.config.get("image_format", "jpeg")
        yield tasks.convert_image(intermediate_file, (self.assets_dir / source.stem).with_suffix(f".{format}"), format=format)

    def process_assets(self, ctx):
        return []
    
    def create_dist(self, ctx):
        yield tasks.create_directory(self.dist_dir / "site" / "assets")
        yield tasks.create_directory(self.build_dir)
