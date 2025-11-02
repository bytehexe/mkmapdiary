import logging
import sys
from pathlib import Path
from typing import Any, Dict, Iterator, List, MutableMapping, Optional, Union

import jsonschema
import yaml
from identify import identify

from mkmapdiary.lib.asset import AssetRecord
from mkmapdiary.lib.calibration import Calibration
from mkmapdiary.lib.dirs import Dirs

from .lib.assetRegistry import AssetRegistry
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
        cache: MutableMapping,
        scan: bool = True,
    ):
        super().__init__()

        self.__config = config
        self.__cache = cache
        self.__dirs = dirs

        self.__calibration = [
            Calibration(
                timezone=config["site"]["timezone"],
                offset=0,
            ),
        ]

        # Store assets by date and then type
        self.__db = AssetRegistry()
        if scan:
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
    def db(self) -> AssetRegistry:
        """Property to access the database."""
        return self.__db

    @property
    def cache(self) -> MutableMapping:
        """Property to access the cache."""
        return self.__cache

    def toDict(self) -> Dict[str, Any]:
        """Convert this object to a dictionary so that doit can use it."""
        return dict((name, getattr(self, name)) for name in dir(self))

    def __scan(self) -> None:
        """Scan the source directory and identify files and directories."""
        self.handle(self.dirs.source_dir)

    def handle_path(self, source: Path) -> Union[Iterator, List[AssetRecord]]:
        """Handle a source file or directory based on its tags."""

        exclude = set(
            [
                # thumbnail files
                ".DS_Store",
                "Thumbs.db",
                # mkmapdiary config files
                "config.yaml",
                "calibration.yaml",
            ]
        )

        if source.is_file() and source.name in exclude:
            return []

        tags = identify.tags_from_path(str(source))
        logger.info(f"Processing {source} [{' '.join(tags)}]", extra={"icon": "🔍"})

        if not tags:
            logger.warning(f"Warning: No tags for {source}")
            return []

        handler = None
        for tag in tags:
            try:
                handler = getattr(self, f"handle_{tag.replace('-', '_')}")
                break
            except AttributeError:
                continue

        if handler is not None:
            results = handler(source)
            if results is not None:
                return results
            else:
                return []

        ext = ("_".join(x[1:] for x in source.suffixes)).lower()
        try:
            handler = getattr(self, f"handle_ext_{ext}")
        except AttributeError:
            pass

        if handler is not None:
            results = handler(source)
            if results is not None:
                return results
            else:
                return []

        logger.warning(
            f"No handler for {source} with tags {tags} and extension '{ext}'",
        )
        return []

    def handle(self, source: Path) -> None:
        results = self.handle_path(source)
        if results:
            self.add_assets(list(results))

    def handle_directory(self, source: Path) -> None:
        """Handle a directory by processing its contents."""

        calibration_file = source / "calibration.yaml"
        if calibration_file.is_file():
            self.__push_calibration(calibration_file)

        for item in source.iterdir():
            self.handle(item)

        if calibration_file.is_file():
            self.__pop_calibration()

    def __push_calibration(self, calibration_file: Path) -> None:
        """Push a new calibration onto the stack."""

        with open(calibration_file) as f:
            data = yaml.safe_load(f)

        schema_path = Path(__file__).parent / "resources" / "calibrate_schema.yaml"
        with schema_path.open() as f:
            schema = yaml.safe_load(f)

        try:
            jsonschema.validate(instance=data, schema=schema)
        except jsonschema.ValidationError as e:
            logger.error(f"Validation error in {calibration_file}: {e.message}")
            sys.exit(1)

        timezone = data.get("calibration", {}).get(
            "timezone", self.__calibration[-1].timezone
        )
        offset = data.get("calibration", {}).get(
            "offset", self.__calibration[-1].offset
        )

        self.__calibration.append(Calibration(timezone=timezone, offset=offset))
        logger.debug(
            f"Applied calibration from {calibration_file}: timezone={timezone}, offset={offset}",
            extra={"icon": "🛠️"},
        )

    def __pop_calibration(self) -> None:
        """Pop the last calibration from the stack."""
        self.__calibration.pop()

    def handle_symlink(self, source: Path) -> None:
        """Handle a symlink by resolving its target."""
        target = source.resolve()
        self.handle(target)

    def add_assets(self, assets: Optional[List[AssetRecord]]) -> None:
        """Add an asset to the list."""

        if assets is None:
            return

        # Adjust timestamps based on current calibration

        for asset in assets:
            # asset.datetime.replace(tzinfo=ZoneInfo(self.calibration.timezone))
            # asset.datetime += timedelta(seconds=self.calibration.offset)
            # asset.datetime = asset.datetime.astimezone(ZoneInfo("UTC"))
            self.db.add_asset(asset)
