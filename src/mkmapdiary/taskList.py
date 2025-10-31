import logging
from datetime import timedelta
from pathlib import Path
from typing import Any, Dict, NamedTuple

import yaml
from identify import identify
from zoneinfo import ZoneInfo

from mkmapdiary.cache import Cache
from mkmapdiary.lib.dirs import Dirs

from .db import Db
from .tasks import (
    AudioTask,
    Cr2Task,
    DayPageTask,
    GalleryTask,
    GeojsonTask,
    GPXTask,
    ImageTask,
    JournalTask,
    MarkdownTask,
    QstarzTask,
    SiteTask,
    TagsTask,
    TextTask,
)

logger = logging.getLogger(__name__)

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
    GPXTask,
    QstarzTask,
    TagsTask,
]


class Calibration(NamedTuple):
    timezone: str
    offset: int


class TaskList(*tasks):  # type: ignore
    """
    Generates task lists based on source directory and configuration.

    The TaskList identifies files and directories based on tags and lists
    them accordingly.
    """

    def __init__(
        self,
        config: Dict[str, Any],
        dirs: Dirs,
        cache: Cache,
    ):
        super().__init__()

        self.__config = config
        self.__cache = cache
        self.__dirs = dirs

        self.__calibration = [
            Calibration(
                timezone=config["site"]["timezone"],
                offset=0,
            )
        ]

        # Store assets by date and then type
        self.__db = Db()
        self.__scan()

    @property
    def dirs(self) -> Dirs:
        """Property to access the directories."""
        return self.__dirs

    @property
    def config(self) -> Dict[str, Any]:
        """Property to access the configuration."""
        return self.__config

    @property
    def calibration(self) -> Calibration:
        """Property to access the current calibration."""
        return self.__calibration[-1]

    @property
    def db(self) -> Db:
        """Property to access the database."""
        return self.__db

    @property
    def cache(self) -> Cache:
        """Property to access the cache."""
        return self.__cache

    def toDict(self):
        """Convert this object to a dictionary so that doit can use it."""
        return dict((name, getattr(self, name)) for name in dir(self))

    def __scan(self):
        """Scan the source directory and identify files and directories."""
        self.handle(self.dirs.source_dir)

    def handle(self, source: Path):
        """Handle a source file or directory based on its tags."""

        if source.is_file() and source.name == "config.yaml":
            return

        tags = identify.tags_from_path(str(source))
        logger.info(f"Processing {source} [{' '.join(tags)}]", extra={"icon": "🔍"})

        if not tags:
            logger.warning(f"Warning: No tags for {source}")
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

        logger.warning(
            f"No handler for {source} with tags {tags} and extension '{ext}'"
        )

    def handle_directory(self, source: Path):
        """Handle a directory by processing its contents."""

        calibration_file = source / "calibration.yaml"
        if calibration_file.is_file():
            self.__push_calibration(calibration_file)

        for item in source.iterdir():
            self.handle(item)

        if calibration_file.is_file():
            self.__pop_calibration()

    def __push_calibration(self, calibration_file: Path):
        """Push a new calibration onto the stack."""

        with open(calibration_file) as f:
            data = yaml.safe_load(f)

        timezone = data.pop("timezone", self.__calibration[-1].timezone)
        offset = data.pop("offset", self.__calibration[-1].offset)

        if data:
            logger.warning(
                f"Unknown calibration options in {calibration_file}: {list(data.keys())}",
            )

        self.__calibration.append(Calibration(timezone=timezone, offset=offset))
        logger.debug(
            f"Applied calibration from {calibration_file}: timezone={timezone}, offset={offset}",
            extra={"icon": "🛠️"},
        )

    def __pop_calibration(self):
        """Pop the last calibration from the stack."""
        self.__calibration.pop()

    def handle_symlink(self, source):
        """Handle a symlink by resolving its target."""
        target = source.resolve()
        self.handle(target)

    def add_assets(self, assets: None):
        """Add an asset to the list."""
        if assets is None:
            return

        # Adjust timestamps based on current calibration

        for asset in assets:
            asset.meta.timestamp.replace(tzinfo=ZoneInfo(self.calibration.timezone))
            asset.meta.timestamp += timedelta(seconds=self.calibration.offset)
            asset.meta.timestamp.astimezone(ZoneInfo("UTC"))
            self.db.add_asset(asset.path, asset.type, asset.meta)
