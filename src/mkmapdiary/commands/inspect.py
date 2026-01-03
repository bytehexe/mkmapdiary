import logging
import tempfile
from collections.abc import MutableMapping
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import click
from tabulate import tabulate

from mkmapdiary import util
from mkmapdiary.lib.config import load_config_file, load_config_param
from mkmapdiary.lib.dirs import Dirs
from mkmapdiary.taskList import TaskList

logger = logging.getLogger(__name__)


@click.command()
@click.option(
    "--tz",
    type=str,
    default="localtime",
    help="Timezone to be used.",
)
@click.argument("source", type=click.Path(path_type=Path), required=True)
def inspect(source: Path, tz: str) -> None:
    """Calibrate camera timestamps using a reference file."""

    try:
        ZoneInfo(tz)
    except ZoneInfoNotFoundError:
        logger.error(f"Invalid timezone: {tz}")
        return

    with tempfile.TemporaryDirectory() as tempdir:
        tempdir_path = Path(tempdir)
        dirs = Dirs(tempdir_path, tempdir_path, tempdir_path, False)

        # Load default config to get all required sections including input_formats
        default_config = dirs.resources_dir / "defaults.yaml"
        config: MutableMapping[str, Any] = load_config_file(default_config)
        # Override timezone
        config = util.deep_update(config, load_config_param(f"site.timezone={tz}"))
        taskList = TaskList(config, dirs, dict(), scan=False)  # type: ignore
        assets = list(taskList.handle_path(source))

        if not assets:
            logger.error("No assets found in the specified source.")
            return

        logger.info(f"Found {len(assets)} assets in the source.")

        for asset in assets:
            taskList.db.add_asset(asset)

        logger.info("Info:\n" + tabulate(*taskList.db.dump()))
