import pathlib
from typing import Any, Dict, Iterator

import whenever
from doit import create_after

from .base.baseTask import BaseTask


class GalleryTask(BaseTask):
    def __init__(self) -> None:
        super().__init__()

    @create_after("geo_correlation")
    def task_build_gallery(self) -> Iterator[Dict[str, Any]]:
        """Generate gallery pages."""

        def _generate_gallery(date: whenever.Date) -> None:
            gallery_path = (
                self.dirs.docs_dir / "templates" / f"{date.format_iso()}_gallery.md"
            )

            gallery_items = []
            geo_items = []

            for i, (asset, _) in enumerate(self.db.get_assets_by_date(date, "image")):
                item = dict(
                    basename=pathlib.PosixPath(asset).name,
                )

                gallery_items.append(item)

                geo_data_item = self.db.get_geo_by_name(str(asset))
                if geo_data_item:
                    geo_item = dict(
                        photo="assets/" + str(asset).split("/")[-1],
                        thumbnail="assets/" + str(asset).split("/")[-1],
                        lat=geo_data_item["latitude"],
                        lng=geo_data_item["longitude"],
                        index=i,
                    )
                    geo_items.append(geo_item)

            gpx = self.db.get_assets_by_date(date, "gpx")
            assert len(gpx) <= 1
            if len(gpx) == 1:
                with open(gpx[0][0]) as f:
                    gpx_data = f.read()
            else:
                gpx_data = None

            with open(gallery_path, "w") as f:
                f.write(
                    self.template(
                        "day_gallery.j2",
                        map_title=self.config["strings"]["map_title"],
                        gallery_title=self.config["strings"]["gallery_title"],
                        gallery_items=gallery_items,
                        geo_items=geo_items,
                        gpx_data=gpx_data,
                        gpx_file=str(gpx[0][0]).split("/")[-1] if gpx else None,
                    ),
                )

        for date in self.db.get_all_dates():
            yield dict(
                name=str(date),
                actions=[(_generate_gallery, [date])],
                targets=[self.dirs.templates_dir / f"{date}_gallery.md"],
                file_dep=self.db.get_all_assets(),
                calc_dep=["get_gpx_deps"],
                task_dep=[f"create_directory:{self.dirs.templates_dir}"],
                uptodate=[True],
            )
