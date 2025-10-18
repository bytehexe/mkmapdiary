from .base.baseTask import BaseTask
import datetime
import pathlib
from doit import create_after
from typing import Callable, Dict, Iterator, List, Tuple, Union, Any


class GalleryTask(BaseTask):
    def __init__(self):
        super().__init__()

    @create_after("gpx2gpx")
    def task_build_gallery(self) -> Iterator[Dict[str, Any]]:
        """Generate gallery pages."""

        def _generate_gallery(date):
            gallery_path = self.docs_dir / "templates" / f"{date}_gallery.md"

            gallery_items = []
            geo_items = []

            for i, (asset, _) in enumerate(self.db.get_assets_by_date(date, "image")):
                item = dict(
                    basename=pathlib.PosixPath(asset).name,
                )

                gallery_items.append(item)

                geo_data_item = self.db.get_geo_by_name(asset)
                if geo_data_item:

                    geo_item = dict(
                        photo="assets/" + asset.split("/")[-1],
                        thumbnail="assets/" + asset.split("/")[-1],
                        lat=geo_data_item["latitude"],
                        lng=geo_data_item["longitude"],
                        index=i,
                    )
                    geo_items.append(geo_item)

            gpx = self.db.get_assets_by_date(date, "gpx")
            assert len(gpx) <= 1
            if len(gpx) == 1:
                with open(gpx[0][0], "r") as f:
                    gpx_data = f.read()
            else:
                gpx_data = None

            with open(gallery_path, "w") as f:
                f.write(
                    self.template(
                        "day_gallery.j2",
                        map_title=self.config["map_title"],
                        gallery_title=self.config["gallery_title"],
                        gallery_items=gallery_items,
                        geo_items=geo_items,
                        gpx_data=gpx_data,
                        gpx_file=gpx[0][0].split("/")[-1] if gpx else None,
                    )
                )

        for date in self.db.get_all_dates():
            yield dict(
                name=str(date),
                actions=[(_generate_gallery, [date])],
                targets=[self.templates_dir / f"{date}_gallery.md"],
                file_dep=self.db.get_all_assets(),
                calc_dep=["get_gpx_deps"],
                task_dep=[f"create_directory:{self.templates_dir}"],
                uptodate=[True],
            )
