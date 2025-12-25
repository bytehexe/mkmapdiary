import logging
import pathlib
from collections.abc import Iterator
from typing import Any

import poiidx
import shapely
import whenever
from doit import create_after

from ..lib.fmt import location_string, time_string
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

                # Ensure asset_data is not None before creating item
                if asset_data is not None:
                    location = location_string(asset_data)
                    time_str, timezone_str = time_string(asset_data, date)

                    if (
                        asset_data.latitude is not None
                        and asset_data.longitude is not None
                    ):
                        language = self.config["site"]["locale"].split("_")[0]
                        location_admin = poiidx.get_administrative_hierarchy_string(
                            shapely.geometry.Point(
                                asset_data.longitude, asset_data.latitude
                            ),
                            language,
                        )
                    else:
                        location_admin = None

                    item = dict(
                        type=asset.type,
                        path=pathlib.PosixPath(asset.path).name,
                        time=time_str,
                        timezone=timezone_str,
                        latitude=asset_data.latitude,
                        longitude=asset_data.longitude,
                        location=location,
                        location_admin=location_admin,
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
