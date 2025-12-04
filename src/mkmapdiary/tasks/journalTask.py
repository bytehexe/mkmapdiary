import logging
import pathlib
from collections.abc import Iterator
from typing import Any

import whenever
from doit import create_after

from .base.baseTask import BaseTask

logger = logging.getLogger(__name__)


class JournalTask(BaseTask):
    def __init__(self) -> None:
        super().__init__()

    @create_after("end_postprocessing")
    def task_build_journal(self) -> Iterator[dict[str, Any]]:
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
                    # Use timestamp_geo if available, fall back to timestamp_utc
                    timestamp_obj = asset_data.timestamp_geo or asset_data.timestamp_utc

                    if timestamp_obj:
                        # Format time
                        time_str = (
                            timestamp_obj.format_iso()
                            .split("T")[1]
                            .split("+")[0]
                            .split("-")[0]
                            .split("Z")[0][:8]
                        )

                        # Extract timezone info
                        if asset_data.timestamp_geo and hasattr(
                            asset_data.timestamp_geo, "tz"
                        ):
                            timezone_str = str(asset_data.timestamp_geo.tz)
                        else:
                            timezone_str = "UTC"
                    else:
                        time_str = ""
                        timezone_str = ""

                    item = dict(
                        type=asset.type,
                        path=pathlib.PosixPath(asset.path).name,
                        time=time_str,
                        timezone=timezone_str,
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
