import pathlib
from datetime import datetime
from typing import Any, Dict, Iterator

from doit import create_after

from .base.baseTask import BaseTask


class JournalTask(BaseTask):
    def __init__(self):
        super().__init__()

    @create_after("gpx2gpx")
    def task_build_journal(self) -> Iterator[Dict[str, Any]]:
        """Generate journal pages."""

        def _generate_journal(date):
            gallery_path = self.docs_dir / "templates" / f"{date}_journal.md"

            assets = []

            for asset, asset_type in self.db.get_assets_by_date(
                date, ("markdown", "audio")
            ):
                metadata = self.db.get_metadata(asset)

                if (
                    metadata["latitude"] is not None
                    and metadata["longitude"] is not None
                ):
                    north_south = "N" if metadata["latitude"] >= 0 else "S"
                    east_west = "E" if metadata["longitude"] >= 0 else "W"
                    location = f"{abs(metadata['latitude']):.4f}° {north_south}, {abs(metadata['longitude']):.4f}° {east_west}"
                else:
                    location = None

                item = dict(
                    type=asset_type,
                    path=pathlib.PosixPath(asset).name,
                    time=datetime.fromisoformat(metadata["timestamp"]).strftime("%X"),
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
                    )
                )

        for date in self.db.get_all_dates():
            yield dict(
                name=str(date),
                actions=[(_generate_journal, [date])],
                targets=[self.docs_dir / "templates" / f"{date}_journal.md"],
                file_dep=self.db.get_all_assets(),
                calc_dep=["get_gpx_deps"],
                task_dep=[f"create_directory:{self.templates_dir}"],
                uptodate=[True],
            )
