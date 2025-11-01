import logging
import pathlib
from datetime import datetime
from typing import Any, Dict, Iterator

import whenever
from doit import create_after

from .base.baseTask import BaseTask

logger = logging.getLogger(__name__)


class JournalTask(BaseTask):
    def __init__(self) -> None:
        super().__init__()

    @create_after("gpx2gpx")
    def task_build_journal(self) -> Iterator[Dict[str, Any]]:
        """Generate journal pages."""

        def _generate_journal(date: whenever.Date) -> None:
            gallery_path = (
                self.dirs.docs_dir / "templates" / f"{date.format_iso()}_journal.md"
            )

            assets = []

            for asset, asset_type in self.db.get_assets_by_date(
                date,
                ("markdown", "audio"),
            ):
                logger.debug(f"Processing asset: {asset} of type {asset_type}")
                metadata = self.db.get_metadata(str(asset))

                if (
                    metadata is not None
                    and metadata["latitude"] is not None
                    and metadata["longitude"] is not None
                ):
                    # Type assertions since we've checked metadata is not None
                    latitude = metadata["latitude"]
                    longitude = metadata["longitude"]
                    assert isinstance(latitude, (int, float)), (
                        "Latitude should be numeric"
                    )
                    assert isinstance(longitude, (int, float)), (
                        "Longitude should be numeric"
                    )

                    north_south = "N" if latitude >= 0 else "S"
                    east_west = "E" if longitude >= 0 else "W"
                    location = f"{abs(latitude):.4f}° {north_south}, {abs(longitude):.4f}° {east_west}"
                else:
                    location = None

                # Ensure metadata is not None before creating item
                if metadata is not None:
                    timestamp = metadata["timestamp"]
                    assert isinstance(timestamp, str), "Timestamp should be a string"

                    item = dict(
                        type=asset_type,
                        path=pathlib.PosixPath(asset).name,
                        time=datetime.fromisoformat(timestamp).strftime("%X"),
                        latitude=metadata["latitude"],
                        longitude=metadata["longitude"],
                        location=location,
                        id=metadata["id"],
                    )
                    assets.append(item)

            with open(gallery_path, "w") as f:
                f.write(
                    self.template(
                        "day_journal.j2",
                        journal_title=self.config["strings"]["journal_title"],
                        audio_title=self.config["strings"]["audio_title"],
                        assets=assets,
                    ),
                )

        for date in self.db.get_all_dates():
            yield dict(
                name=str(date),
                actions=[(_generate_journal, [date])],
                targets=[
                    self.dirs.docs_dir / "templates" / f"{date.format_iso()}_journal.md"
                ],
                file_dep=self.db.get_all_assets(),
                calc_dep=["get_gpx_deps"],
                task_dep=[
                    f"create_directory:{self.dirs.templates_dir}",
                    "geo_correlation",
                ],
                uptodate=[True],
            )
