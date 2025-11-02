import bisect
import logging
from pathlib import Path, PosixPath
from typing import Any, Dict, Iterator, List, Set, Tuple

import gpxpy
import gpxpy.gpx
import tzfpy
import whenever
from doit import create_after
from tabulate import tabulate
from whenever import Date

from mkmapdiary.gpxCreator import GpxCreator
from mkmapdiary.lib.asset import AssetRecord
from mkmapdiary.tasks.base.httpRequest import HttpRequest

logger = logging.getLogger(__name__)


class GPXTask(HttpRequest):
    def __init__(self) -> None:
        super().__init__()
        self.__sources: list[PosixPath] = []

    def handle_gpx(self, source: PosixPath) -> List[Any]:
        self.__sources.append(source)

        # Do not yield any assets yet; at this point it
        # is difficult to determine which dates are contained,
        # due to asset splitting.
        # Instead we will resort to delayed task creation.
        return []

    def __get_contained_dates(self, source: PosixPath) -> Set[Date]:
        # Collect all dates in the gpx file
        dates: Set[Date] = set()
        with open(source, encoding="utf-8") as f:
            gpx = gpxpy.parse(f)
        for wpt in gpx.waypoints:
            if wpt.time is not None:
                dates.add(Date.from_py_date(wpt.time.date()))
        for trk in gpx.tracks:
            for seg in trk.segments:
                for pt in seg.points:
                    if pt.time is not None:
                        dates.add(Date.from_py_date(pt.time.date()))
        for rte in gpx.routes:
            for rte_pt in rte.points:
                if rte_pt.time is not None:
                    dates.add(Date.from_py_date(rte_pt.time.date()))

        return dates

    def __generate_destination_filename(self, date: Date) -> Path:
        filename = (self.dirs.assets_dir / date.format_iso()).with_suffix(
            ".gpx",
        )
        return filename

    def __gpx2gpx(self, date: Date, dst: Path, gpx_source: bool) -> None:
        if gpx_source:
            sources = self.__sources
        else:
            sources = []

        logger.debug("Fetching Geofabrik region data...")
        index_data = self.httpRequest("https://download.geofabrik.de/index-v1.json")
        assert isinstance(index_data, dict), "Invalid index data received"

        gc = GpxCreator(index_data, date, sources, self.db, self.dirs.region_cache_dir)
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
        dates: Set[whenever.Date] = set()
        for source in self.__sources:
            if not source.exists():
                raise FileNotFoundError(f"Source file not found: {source}")
            dates.update(self.__get_contained_dates(source))

        for date in dates:
            dst = self.__generate_destination_filename(date)

            asset = AssetRecord(
                path=dst,
                type="gpx",
                display_date=date,
            )

            self.db.add_asset(asset)

            yield {
                "name": date.format_iso(),
                "actions": [(self.__gpx2gpx, [date, dst, True])],
                "file_dep": [str(src) for src in self.__sources],
                "task_dep": ["geo_correlation", "qstarz2gpx"],
                "targets": [str(dst)],
                "clean": True,
            }

        journal_dates = set(self.db.get_geotagged_journals()) - dates
        for date in journal_dates:
            dst = self.__generate_destination_filename(date)
            yield {
                "name": date.format_iso(),
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

        def _gpx_deps() -> Dict[str, List[str]]:
            self.__debug_dump_gpx()
            return {
                "file_dep": [x[0] for x in self.db.get_assets_by_type("gpx")],
            }

        return {
            "task_dep": ["gpx2gpx"],
            "file_dep": [str(src) for src in self.__sources],
            "actions": [_gpx_deps],
        }

    def __get_timed_coords(
        self, gpx: gpxpy.gpx.GPX, coords: List[Tuple[whenever.Instant, float, float]]
    ) -> None:
        # Extract coordinates from GPX format (lat, lon) and store as (time, lon, lat) for internal use
        for wpt in gpx.waypoints:
            if wpt.time is not None:
                coords.append(
                    (
                        whenever.Instant.from_py_datetime(wpt.time),
                        wpt.longitude,
                        wpt.latitude,
                    )
                )
        for trk in gpx.tracks:
            for seg in trk.segments:
                for pt in seg.points:
                    if pt.time is not None:
                        coords.append(
                            (
                                whenever.Instant.from_py_datetime(pt.time),
                                pt.longitude,
                                pt.latitude,
                            )
                        )
        for rte in gpx.routes:
            for rte_pt in rte.points:
                if rte_pt.time is not None:
                    coords.append(
                        (
                            whenever.Instant.from_py_datetime(rte_pt.time),
                            rte_pt.longitude,
                            rte_pt.latitude,
                        )
                    )

    def task_geo_correlation(self) -> Dict[str, Any]:
        def _update_positions() -> None:
            coords: list[tuple[whenever.Instant, float, float]] = []
            for path in self.__sources:
                with open(path, encoding="utf-8") as f:
                    gpx = gpxpy.parse(f)
                self.__get_timed_coords(gpx, coords)
            coords.sort(key=lambda x: x[0])
            for asset_id, asset_time in self.db.get_unpositioned_assets():
                # Find closest coordinate by time
                if asset_time is not None:
                    assert isinstance(asset_time, whenever.Instant), (
                        "Asset time should be a whenever.Instant"
                    )
                    asset_datetime: whenever.Instant = asset_time
                    candidates = []
                    pos = bisect.bisect_left(coords, asset_datetime, key=lambda x: x[0])
                    if pos > 0:
                        candidates.append(coords[pos - 1])
                    if pos < len(coords):
                        candidates.append(coords[pos])
                    if candidates:
                        closest = min(
                            candidates, key=lambda x: abs(x[0] - asset_datetime)
                        )
                        diff_w: whenever.TimeDelta = closest[0] - asset_datetime
                        diff = diff_w.in_seconds()
                        if (
                            abs(diff)
                            < self.config["features"]["geo_correlation"][
                                "max_time_diff"
                            ]
                        ):
                            # closest contains (time, lon, lat), database expects separate lat, lon parameters
                            self.db.update_asset_position(
                                asset_id,
                                closest[2],
                                closest[1],
                                bool(
                                    diff
                                ),  # Convert to bool as expected by the function
                            )

            # Assigning timestamp_geo to assets
            for asset in self.db.assets:
                if asset.timestamp_utc is None:
                    # No UTC timestamp to base geo timestamp on
                    continue

                if asset.latitude is None or asset.longitude is None:
                    # Not enough data to determine timezone
                    logger.warning(
                        f"Asset '{asset.path}' is missing geo information, assigning localtime."
                    )
                    asset.timestamp_geo = asset.timestamp_utc.to_system_tz()
                    continue

                if asset.timestamp_geo is not None:
                    # Already has a geo timestamp
                    continue

                asset_tz = tzfpy.get_tz(
                    lng=asset.longitude,
                    lat=asset.latitude,
                )
                asset.timestamp_geo = asset.timestamp_utc.to_tz(asset_tz)

            # Assigning display date to assets
            last_date = whenever.Date.MIN
            for asset in sorted(
                self.db.assets, key=lambda x: x.timestamp_utc or whenever.Instant.MIN
            ):
                if asset.timestamp_geo is None:
                    continue

                temp_date = asset.timestamp_geo.date()

                # Ensure non-decreasing display dates (avoid going back in time)
                if temp_date < last_date:
                    asset.display_date = last_date
                else:
                    asset.display_date = temp_date
                    last_date = temp_date

            self.db.has_display_date = True

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

    def __debug_dump_gpx(self) -> None:
        logger.debug("GPX dump:\n" + tabulate(*self.db.dump("gpx")))
