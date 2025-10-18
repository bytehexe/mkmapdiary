from .base.baseTask import BaseTask
import gpxpy
import gpxpy.gpx
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import hdbscan
import numpy as np
from tdgen.geoCluster import GeoCluster
from doit import create_after
from tabulate import tabulate
import warnings
import sys
import bisect

class GPXTask(BaseTask):
    def __init__(self):
        super().__init__()
        self.__sources = []

    def handle_gpx(self, source):
        self.__sources.append(source)

        # Do not yield any assets yet; at this point it
        # is difficult to determine which dates are contained,
        # due to asset splitting.
        # Instead we will resort to delayed task creation.
        return []

    def __get_contained_dates(self, source):
        # Collect all dates in the gpx file
        dates = set()
        with open(source, "r", encoding="utf-8") as f:
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
        filename = (self.assets_dir / date.strftime("%Y-%m-%d")).with_suffix(".gpx")
        return filename

    def __gpx2gpx(self, date, dst):
        gpx_out = gpxpy.gpx.GPX()

        coords = []

        for source in self.__sources:    
            with open(source, "r", encoding="utf-8") as f:
                gpx = gpxpy.parse(f)
            for mwpt in gpx.waypoints:
                if mwpt.time is not None and mwpt.time.date() == date:
                    gpx_out.waypoints.append(mwpt)
            for trk in gpx.tracks:
                new_trk = gpxpy.gpx.GPXTrack(name=trk.name, description=trk.description)
                for seg in trk.segments:
                    new_seg = gpxpy.gpx.GPXTrackSegment()
                    for pt in seg.points:
                        if pt.time is not None and pt.time.date() == date:
                            new_seg.points.append(pt)
                            coords.append([pt.latitude, pt.longitude])
                    if len(new_seg.points) > 0:
                        new_trk.segments.append(new_seg)
                if len(new_trk.segments) > 0:
                    gpx_out.tracks.append(new_trk)
            for rte in gpx.routes:
                new_rte = gpxpy.gpx.GPXRoute(name=rte.name, description=rte.description)
                for pt in rte.points:
                    if pt.time is not None and pt.time.date() == date:
                        new_rte.points.append(pt)
                if len(new_rte.points) > 0:
                    gpx_out.routes.append(new_rte)

        if len(coords) > 10:
            coords = np.array(coords)

            # Fit HDBSCAN
            clusterer = hdbscan.HDBSCAN(min_cluster_size=1000, metric='haversine')
            with warnings.catch_warnings():
                warnings.simplefilter(action='ignore', category=FutureWarning)
                clusterer.fit(np.radians(coords))

            labels = clusterer.labels_
            for label in set(labels):
                if label == -1:
                    continue
                cluster_coords = coords[labels == label]
                cluster = GeoCluster(cluster_coords)

                if cluster.radius > 10000:
                    # Ignore overly large clusters
                    continue

                mlat, mlon = cluster.mass_point
                mwpt = gpxpy.gpx.GPXWaypoint(
                    latitude=mlat, longitude=mlon,
                    name=f"Cluster {label}",
                    description=f"Cluster of {len(cluster_coords)} points and radius {cluster.radius:.1f} m",
                    symbol="cluster-mass"
                )
                gpx_out.waypoints.append(mwpt)
                clat, clon = cluster.midpoint
                cwpt = gpxpy.gpx.GPXWaypoint(                
                    latitude=clat, longitude=clon,
                    name=f"Cluster {label} Center",
                    description=f"Center of cluster {label}",
                    symbol="cluster-center",
                    position_dilution=cluster.radius
                )
                gpx_out.waypoints.append(cwpt)

        with open(dst, "w", encoding="utf-8") as f:
            f.write(gpx_out.to_xml())

    @create_after("geo2gpx", target_regex=r'.*\.gpx')
    def task_gpx2gpx(self):

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
                {
                    "date": datetime.combine(date, datetime.min.time()),
                }
            )

            yield {
                "name": date.isoformat(),
                "actions": [(self.__gpx2gpx, [date, dst])],
                "file_dep": [str(src) for src in self.__sources],
                "targets": [str(dst)],
                "clean": True,
            }

    @create_after("gpx2gpx")
    def task_get_gpx_deps(self):
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
            "task_dep": ["gpx2gpx:*"],
            "file_dep": [str(src) for src in self.__sources],
            "actions": [_gpx_deps],
            "verbosity": 2,
        }
    
    def __get_timed_coords(self, gpx, coords):
        for wpt in gpx.waypoints:
            if wpt.time is not None:
                coords.append((wpt.time, wpt.latitude, wpt.longitude))
        for trk in gpx.tracks:
            for seg in trk.segments:
                for pt in seg.points:
                    if pt.time is not None:
                        coords.append((pt.time, pt.latitude, pt.longitude))
        for rte in gpx.routes:
            for pt in rte.points:
                if pt.time is not None:
                    coords.append((pt.time, pt.latitude, pt.longitude))

    def task_geo_correlation(self):
        def _update_positions():
            tz = ZoneInfo(self.config["geo_correlation"]["timezone"])
            offset = timedelta(seconds=self.config["geo_correlation"]["time_offset"])

            coords = []
            for path in self.__sources:
                with open(path, "r", encoding="utf-8") as f:
                    gpx = gpxpy.parse(f)
                self.__get_timed_coords(gpx, coords)
            coords.sort(key=lambda x: x[0])
            for asset_id, asset_time in self.db.get_unpositioned_assets():
                # Find closest coordinate by time
                asset_time = datetime.fromisoformat(asset_time).replace(tzinfo=tz) + offset
                candidates = []
                pos = bisect.bisect_left(coords, asset_time, key=lambda x: x[0])
                if pos > 0:
                    candidates.append(coords[pos-1])
                if pos < len(coords):
                    candidates.append(coords[pos])
                if candidates:
                    closest = min(candidates, key=lambda x: abs(x[0] - asset_time))
                    diff = (closest[0] - asset_time).total_seconds()
                    if abs(diff) < 120:
                        self.db.update_asset_position(asset_id, closest[1], closest[2], int(diff))
            sys.stderr.write(tabulate(*self.db.dump()))
            sys.stderr.write("\n")
            sys.stderr.flush()

        return {
            "actions": [_update_positions],
            "file_dep": [str(src) for src in self.__sources],
            "verbosity": 2,
        }
        
    def __debug_dump_gpx(self):
        sys.stderr.write(tabulate(*self.db.dump("gpx")))
        sys.stderr.write("\n")
        sys.stderr.flush()