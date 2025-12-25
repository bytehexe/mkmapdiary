import dataclasses
from abc import abstractmethod
from collections.abc import Iterator
from typing import Any

import poiidx
import shapely
import whenever
from doit import create_after
from whenever import Date

from ..lib.fmt import location_string, time_string
from ..lib.highlights import Highlights
from ..lib.statistics import Statistics
from .base.baseTask import BaseTask


class GalleryTask(BaseTask):
    def __init__(self) -> None:
        super().__init__()

    @property
    @abstractmethod
    def track_statistics(self) -> dict[Date, Statistics]:
        raise NotImplementedError("GalleryTask does not provide track statistics.")

    @create_after("end_postprocessing")
    def task_build_gallery(self) -> Iterator[dict[str, Any]]:
        """Generate gallery pages."""

        def _generate_gallery(date: whenever.Date) -> None:
            gallery_path = (
                self.dirs.docs_dir / "templates" / f"{date.format_iso()}_gallery.md"
            )

            images = self.db.get_assets_by_date(date, "image")
            page_info = Highlights(images, self.config, day_page=True)

            gallery_items = []
            geo_items = []

            for i, asset in enumerate(images):
                model_dict = dataclasses.asdict(asset)

                if asset.latitude is not None and asset.longitude is not None:
                    model_dict["location_admin"] = (
                        poiidx.get_administrative_hierarchy_string(
                            shapely.geometry.Point(asset.longitude, asset.latitude)
                        )
                    )
                else:
                    model_dict["location_admin"] = None
                location = location_string(asset)
                time_str, timezone_str = time_string(asset, date)

                model_dict["time"] = time_str
                model_dict["timezone"] = timezone_str
                model_dict["location"] = location

                gallery_items.append(model_dict)

                if asset.is_bad or asset.is_duplicate:
                    continue

                geo_asset = self.db.get_geotagged_asset_by_path(asset.path)
                if geo_asset:
                    geo_item = dict(
                        photo="assets/" + str(asset.path).split("/")[-1],
                        thumbnail="assets/" + str(asset.path).split("/")[-1],
                        lat=geo_asset.latitude,
                        lng=geo_asset.longitude,
                        index=i + len(page_info.gallery_assets),
                        quality=geo_asset.quality,
                        low_entropy=int(
                            asset.entropy is not None and asset.entropy < 6.5
                        ),
                    )
                    geo_items.append(geo_item)

            geo_items.sort(key=lambda x: (-x["low_entropy"], x["quality"] or 0))  # type: ignore

            gpx = self.db.get_assets_by_date(date, "gpx")
            assert len(gpx) <= 1
            if len(gpx) == 1:
                with open(gpx[0].path) as f:
                    gpx_data = f.read()
            else:
                gpx_data = None

            track_statistics = self.track_statistics.get(date, None)

            with open(gallery_path, "w") as f:
                f.write(
                    self.template(
                        "day_gallery.j2",
                        has_bad_photos=any(
                            asset["quality"] is not None and asset["quality"] < 0.1
                            for asset in gallery_items
                        ),
                        has_duplicates=any(
                            asset["is_duplicate"] for asset in gallery_items
                        ),
                        highlight_images=page_info.gallery_assets,
                        gallery_items=gallery_items,
                        geo_items=geo_items,
                        gpx_data=gpx_data,
                        gpx_file=str(gpx[0].path).split("/")[-1] if gpx else None,
                        track_statistics=track_statistics,
                    ),
                )

        for date in self.db.get_all_dates():
            yield dict(
                name=str(date),
                actions=[(_generate_gallery, [date])],
                targets=[self.dirs.templates_dir / f"{date}_gallery.md"],
                file_dep=[str(asset.path) for asset in self.db.get_all_assets()],
                calc_dep=["get_gpx_deps"],
                task_dep=[f"create_directory:{self.dirs.templates_dir}"],
                uptodate=[False],
            )
