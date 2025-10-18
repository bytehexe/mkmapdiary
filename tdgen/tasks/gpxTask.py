from .base.baseTask import BaseTask
import gpxpy
import gpxpy.gpx
import dateutil.parser
from datetime import datetime
import hdbscan
import numpy as np
from tdgen.geoCluster import GeoCluster

class GPXTask(BaseTask):
    def __init__(self):
        super().__init__()
        self.__sources = {}
        self.__dates = set()

    def handle_gpx(self, source, additional_dates=None):
        if source.is_file():
            dates = self.__get_contained_dates(source)
        else:
            dates = set()

        if additional_dates:
            dates.update(additional_dates)

        self.__sources[source] = dates

        missing_dates = dates - self.__dates
        for date in missing_dates:
            yield self.Asset(
                self.__generate_destination_filename(date),
                "gpx",
                {
                    "date": datetime.combine(date, datetime.min.time())
                }
            )

        self.__dates.update(dates)

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
            clusterer.fit(np.radians(coords))

            labels = clusterer.labels_
            for label in set(labels):
                if label == -1:
                    continue
                cluster_coords = coords[labels == label]
                cluster = GeoCluster(cluster_coords)
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

    def task_gpx2gpx(self):
        for date in self.__dates:
            dst = self.__generate_destination_filename(date)
            yield {
                "name": date.isoformat(),
                "actions": [(self.__gpx2gpx, [date, dst])],
                "file_dep": [str(src) for src in self.__sources],
                "targets": [str(dst)],
                "clean": True,
            }