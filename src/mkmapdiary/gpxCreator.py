import gpxpy
import hdbscan
import numpy as np
from mkmapdiary.geoCluster import GeoCluster
import warnings


class GpxCreator:
    def __init__(self, date, sources, db):
        self.__coords = []
        self.__gpx_out = gpxpy.gpx.GPX()
        self.__sources = sources
        self.__date = date
        self.__db = db

        self.__init()

    def __init(self):
        for source in self.__sources:
            self.__load_source(source)
        self.__compute_clusters()
        self.__add_journal_markers()

    def __load_source(self, source):
        with open(source, "r", encoding="utf-8") as f:
            gpx = gpxpy.parse(f)
        for mwpt in gpx.waypoints:
            if mwpt.time is not None and mwpt.time.date() == self.__date:
                self.__gpx_out.waypoints.append(mwpt)
        for trk in gpx.tracks:
            new_trk = gpxpy.gpx.GPXTrack(name=trk.name, description=trk.description)
            for seg in trk.segments:
                new_seg = gpxpy.gpx.GPXTrackSegment()
                for pt in seg.points:
                    if pt.time is not None and pt.time.date() == self.__date:
                        new_seg.points.append(pt)
                        self.__coords.append([pt.latitude, pt.longitude])
                if len(new_seg.points) > 0:
                    new_trk.segments.append(new_seg)
            if len(new_trk.segments) > 0:
                self.__gpx_out.tracks.append(new_trk)
        for rte in gpx.routes:
            new_rte = gpxpy.gpx.GPXRoute(name=rte.name, description=rte.description)
            for pt in rte.points:
                if pt.time is not None and pt.time.date() == self.__date:
                    new_rte.points.append(pt)
            if len(new_rte.points) > 0:
                self.__gpx_out.routes.append(new_rte)

    def __compute_clusters(self):
        if len(self.__coords) < 10:
            return

        self.__coords = np.array(self.__coords)

        # Fit HDBSCAN
        clusterer = hdbscan.HDBSCAN(min_cluster_size=1000, metric="haversine")
        with warnings.catch_warnings():
            warnings.simplefilter(action="ignore", category=FutureWarning)
            clusterer.fit(np.radians(self.__coords))

        labels = clusterer.labels_
        for label in set(labels):
            if label == -1:
                continue
            cluster_coords = self.__coords[labels == label]
            cluster = GeoCluster(cluster_coords)

            if cluster.radius > 10000:
                # Ignore overly large clusters
                continue

            mlat, mlon = cluster.mass_point
            mwpt = gpxpy.gpx.GPXWaypoint(
                latitude=mlat,
                longitude=mlon,
                name=f"Cluster {label}",
                description=f"Cluster of {len(cluster_coords)} points and radius {cluster.radius:.1f} m",
                symbol="cluster-mass",
            )
            self.__gpx_out.waypoints.append(mwpt)
            clat, clon = cluster.midpoint
            cwpt = gpxpy.gpx.GPXWaypoint(
                latitude=clat,
                longitude=clon,
                name=f"Cluster {label} Center",
                description=f"Center of cluster {label}",
                symbol="cluster-center",
                position_dilution=cluster.radius,
            )
            self.__gpx_out.waypoints.append(cwpt)

    def __add_journal_markers(self):
        for asset, asset_type in self.__db.get_assets_by_date(
            self.__date, ("markdown", "audio")
        ):
            geo = self.__db.get_geo_by_name(asset)
            if geo is None:
                continue
            metadata = self.__db.get_metadata(asset)
            wpt = gpxpy.gpx.GPXWaypoint(
                latitude=geo["latitude"],
                longitude=geo["longitude"],
                name="Journal Entry",
                comment=f"{metadata['id']}",
                symbol=f"{asset_type}-journal-entry",
            )
            self.__gpx_out.waypoints.append(wpt)

    def to_xml(self):
        return self.__gpx_out.to_xml()
