import bisect
import logging
from datetime import datetime, timedelta
from pathlib import PosixPath
from typing import Any, Dict, Iterator, List

import gpxpy
import gpxpy.gpx
from doit import create_after
from tabulate import tabulate
from zoneinfo import ZoneInfo

from mkmapdiary.gpxCreator import GpxCreator
from mkmapdiary.lib.asset import AssetMeta

from .base.baseTask import BaseTask

logger = logging.getLogger(__name__)


class GPXTask(BaseTask):
    def __init__(self):
        super().__init__()
        self.__sources = []

    def handle_gpx(self, source: PosixPath) -> List[Any]:
        self.__sources.append(source)

        # Do not yield any assets yet; at this point it
        # is difficult to determine which dates are contained,
        # due to asset splitting.
        # Instead we will resort to delayed task creation.
        return []

    def __get_contained_dates(self, source):
        # Collect all dates in the gpx file
        dates = set()
        with open(source, encoding="utf-8") as f:
            gpx = gpxpy.parse(f)
        for wpt in gpx.waypoints:
            dates.add(wpt.time.date() if wpt.time is not None else None)
        for trk in gpx.tracks:
            for seg in trk.segments:
                for pt in seg.points:
                    dates.add(pt.time.date() if pt.time is not None else None)
        for rte in gpx.routes:
            for pt in rte.points:
                dates.add(pt.time.date() if pt.time is not None else None)

        try:
            dates.remove(None)
        except KeyError:
            pass

        return dates

    def __generate_destination_filename(self, date):
        filename = (self.dirs.assets_dir / date.strftime("%Y-%m-%d")).with_suffix(
            ".gpx",
        )
        return filename

    def __gpx2gpx(self, date, dst, gpx_source):
        if gpx_source:
            sources = self.__sources
        else:
            sources = []

        gc = GpxCreator(date, sources, self.db, self.dirs.region_cache_dir)
        gpx_out = gc.to_xml()

        with open(dst, "w", encoding="utf-8") as f:
            f.write(gpx_out)

    def task_pre_gpx(self) -> Dict[str, Any]:
        # Ensure that the assets and files directories exist
        return {
            "actions": None,
            "task_dep": [
                f"create_directory:{self.dirs.assets_dir}",
                f"create_directory:{self.dirs.files_dir}",
                "geo2gpx",
                "qstarz2gpx",
            ],
        }

    @create_after("pre_gpx", target_regex=r".*\.gpx")
    def task_gpx2gpx(self) -> Iterator[Dict[str, Any]]:
        # Collect all dates in all source files
        dates = set()
        for source in self.__sources:
            if not source.exists():
                raise FileNotFoundError(f"Source file not found: {source}")
            dates.update(self.__get_contained_dates(source))

        for date in dates:
            dst = self.__generate_destination_filename(date)

            self.db.add_asset(
                str(dst),
                "gpx",
                AssetMeta(
                    timestamp=datetime.combine(date, datetime.min.time()),
                ),
            )

            yield {
                "name": date.isoformat(),
                "actions": [(self.__gpx2gpx, [date, dst, True])],
                "file_dep": [str(src) for src in self.__sources],
                "task_dep": ["geo_correlation", "qstarz2gpx"],
                "targets": [str(dst)],
                "clean": True,
            }

        journal_dates = (
            set(
                datetime.fromisoformat(date).date()
                for date in self.db.get_geotagged_journals()
            )
            - dates
        )
        for date in journal_dates:
            dst = self.__generate_destination_filename(date)
            yield {
                "name": date.isoformat(),
                "actions": [(self.__gpx2gpx, [date, dst, False])],
                "task_dep": ["geo_correlation"],
                "targets": [str(dst)],
                "clean": True,
            }

    @create_after("gpx2gpx")
    def task_get_gpx_deps(self) -> Dict[str, Any]:
        # Explicitely re-introduce dependencies on all gpx files
        # with calc_dep, since file_dep is not computed when used
        # with create_after.
        # See:
        # - https://pydoit.org/task-creation.html#delayed-task-creation
        # - https://pydoit.org/dependencies.html#calculated-dependencies

        def _gpx_deps():
            self.__debug_dump_gpx()
            return {
                "file_dep": [x[0] for x in self.db.get_assets_by_type("gpx")],
            }

        return {
            "task_dep": ["gpx2gpx"],
            "file_dep": [str(src) for src in self.__sources],
            "actions": [_gpx_deps],
        }

    def __get_timed_coords(self, gpx, coords):
        # Extract coordinates from GPX format (lat, lon) and store as (time, lon, lat) for internal use
        for wpt in gpx.waypoints:
            if wpt.time is not None:
                coords.append((wpt.time, wpt.longitude, wpt.latitude))
        for trk in gpx.tracks:
            for seg in trk.segments:
                for pt in seg.points:
                    if pt.time is not None:
                        coords.append((pt.time, pt.longitude, pt.latitude))
        for rte in gpx.routes:
            for pt in rte.points:
                if pt.time is not None:
                    coords.append((pt.time, pt.longitude, pt.latitude))

    def task_geo_correlation(self) -> Dict[str, Any]:
        def _update_positions():
            tz = ZoneInfo(self.config["site"]["timezone"])
            offset = timedelta(
                seconds=self.config["features"]["geo_correlation"]["time_offset"],
            )

            coords = []
            for path in self.__sources:
                with open(path, encoding="utf-8") as f:
                    gpx = gpxpy.parse(f)
                self.__get_timed_coords(gpx, coords)
            coords.sort(key=lambda x: x[0])
            for asset_id, asset_time in self.db.get_unpositioned_assets():
                # Find closest coordinate by time
                asset_time = (
                    datetime.fromisoformat(asset_time).replace(tzinfo=tz) + offset
                )
                candidates = []
                pos = bisect.bisect_left(coords, asset_time, key=lambda x: x[0])
                if pos > 0:
                    candidates.append(coords[pos - 1])
                if pos < len(coords):
                    candidates.append(coords[pos])
                if candidates:
                    closest = min(candidates, key=lambda x: abs(x[0] - asset_time))
                    diff = (closest[0] - asset_time).total_seconds()
                    if (
                        abs(diff)
                        < self.config["features"]["geo_correlation"]["max_time_diff"]
                    ):
                        # closest contains (time, lon, lat), database expects separate lat, lon parameters
                        self.db.update_asset_position(
                            asset_id,
                            closest[2],
                            closest[1],
                            int(diff),  # lat, lon for database
                        )
            logger.debug(
                "Asset positions updated:\n" + tabulate(*self.db.dump()),
                extra={"icon": "🌐"},
            )

        return {
            "actions": [_update_positions],
            "file_dep": [str(src) for src in self.__sources]
            + self.db.get_unpositioned_asset_paths(),
            "uptodate": [False],
        }

    def __debug_dump_gpx(self):
        logger.debug("GPX dump:\n" + tabulate(*self.db.dump("gpx")))
