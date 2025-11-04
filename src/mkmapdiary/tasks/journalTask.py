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

    @create_after("end_gpx")
    def task_build_journal(self) -> Iterator[Dict[str, Any]]:
        """Generate journal pages."""

        def _generate_journal(date: whenever.Date) -> None:
            gallery_path = (
                self.dirs.docs_dir / "templates" / f"{date.format_iso()}_journal.md"
            )

            assets = []

            for asset in self.db.get_assets_by_date(
                date,
                ("markdown", "audio"),
            ):
                logger.debug(f"Processing asset: {asset.path} of type {asset.type}")
                asset_data = self.db.get_asset_by_path(asset.path)

                if (
                    asset_data is not None
                    and asset_data.latitude is not None
                    and asset_data.longitude is not None
                ):
                    # Type assertions since we've checked asset_data is not None
                    latitude = asset_data.latitude
                    longitude = asset_data.longitude
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

                # Ensure asset_data is not None before creating item
                if asset_data is not None:
                    timestamp = (
                        asset_data.timestamp_utc.format_iso()
                        if asset_data.timestamp_utc
                        else None
                    )
                    assert isinstance(timestamp, (str, type(None))), (
                        "Timestamp should be a string or None"
                    )

                    item = dict(
                        type=asset.type,
                        path=pathlib.PosixPath(asset.path).name,
                        time=datetime.fromisoformat(timestamp).strftime("%X")
                        if timestamp
                        else "",
                        latitude=asset_data.latitude,
                        longitude=asset_data.longitude,
                        location=location,
                        id=asset_data.id,
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
                file_dep=[str(asset.path) for asset in self.db.get_all_assets()],
                calc_dep=["get_gpx_deps"],
                task_dep=[
                    f"create_directory:{self.dirs.templates_dir}",
                    "geo_correlation",
                ],
                uptodate=[False],
            )
