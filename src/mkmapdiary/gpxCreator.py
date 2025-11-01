import logging
import warnings
from datetime import date
from pathlib import Path, PosixPath
from typing import Sequence, Union

import gpxpy
import gpxpy.gpx
import hdbscan
import numpy as np
import shapely
from numpy.typing import NDArray

from mkmapdiary.db import Db
from mkmapdiary.geoCluster import GeoCluster
from mkmapdiary.poi.index import Index
from mkmapdiary.util.log import ThisMayTakeAWhile

logger = logging.getLogger(__name__)


class GpxCreator:
    def __init__(
        self,
        date: date,
        sources: Sequence[Union[str, PosixPath]],
        db: Db,
        region_cache_dir: Path,
    ) -> None:
        # FIXME: Inconsistent types
        self.__coords: Union[list[list[float]], NDArray[np.floating]] = []
        self.__gpx_out = gpxpy.gpx.GPX()
        self.__sources = sources
        self.__date = date
        self.__db = db
        self.__region_cache_dir = region_cache_dir

        self.__init()

    def __init(self) -> None:
        logger.debug(f"Creating GPX for date {self.__date}")
        with ThisMayTakeAWhile(logger, "Parsing GPX sources"):
            for source in self.__sources:
                self.__load_source(source)
        with ThisMayTakeAWhile(logger, "Computing clusters"):
            self.__compute_clusters()
        self.__add_journal_markers()

    def __load_source(self, source: Union[str, PosixPath]) -> None:
        with open(source, encoding="utf-8") as f:
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
                        # Store coordinates as (lon, lat) for consistent interface format
                        # Converting from GPX format (lat, lon) to interface format (lon, lat)
                        if isinstance(self.__coords, list):
                            self.__coords.append([pt.longitude, pt.latitude])
                if len(new_seg.points) > 0:
                    new_trk.segments.append(new_seg)
            if len(new_trk.segments) > 0:
                self.__gpx_out.tracks.append(new_trk)
        for rte in gpx.routes:
            new_rte = gpxpy.gpx.GPXRoute(name=rte.name, description=rte.description)
            for rte_pt in rte.points:
                if rte_pt.time is not None and rte_pt.time.date() == self.__date:
                    new_rte.points.append(rte_pt)
            if len(new_rte.points) > 0:
                self.__gpx_out.routes.append(new_rte)

    def __compute_clusters(self) -> None:
        if len(self.__coords) < 10:
            return

        self.__coords = np.array(self.__coords)

        # Fit HDBSCAN
        eps = 10  # meters
        eps_rad = eps / 6371008.8  # convert to radians
        clusterer = hdbscan.HDBSCAN(
            min_cluster_size=1000,
            cluster_selection_epsilon=eps_rad,
            metric="haversine",
        )
        with warnings.catch_warnings():
            warnings.simplefilter(action="ignore", category=FutureWarning)
            clusterer.fit(np.radians(self.__coords))

        labels = clusterer.labels_
        for label in set(labels):
            if label == -1:
                continue
            cluster_coords = self.__coords[labels == label]
            cluster = GeoCluster(cluster_coords)

            if cluster.radius > 1200:
                # Ignore overly large clusters
                continue

            # cluster.mass_point returns (lon, lat) format, convert for GPX which expects (lat, lon)
            mlon, mlat = cluster.mass_point
            mwpt = gpxpy.gpx.GPXWaypoint(
                latitude=mlat,
                longitude=mlon,
                name=f"Cluster {label}",
                description=f"Cluster of {len(cluster_coords)} points and radius {cluster.radius:.1f} m",
                symbol="cluster-mass",
            )
            self.__gpx_out.waypoints.append(mwpt)
            # cluster.midpoint returns (lon, lat) format, convert for GPX which expects (lat, lon)
            clon, clat = cluster.midpoint
            cwpt = gpxpy.gpx.GPXWaypoint(
                latitude=clat,
                longitude=clon,
                name=f"Cluster {label} Center",
                description=f"Center of cluster {label}",
                symbol="cluster-center",
                position_dilution=cluster.radius,
            )
            self.__gpx_out.waypoints.append(cwpt)

            # Add a POI for each cluster center
            logger.info(
                f"Searching POIs near cluster {label} at {clat},{clon}",
                extra={"icon": "📍"},
            )

            index = Index(
                cluster.shape.__geo_interface__, self.__region_cache_dir, keep_pbf=True
            )
            # Convert mass_point (lon, lat) to shapely.Point for Index.get_nearest
            mass_lon, mass_lat = cluster.mass_point
            if mass_lon is not None and mass_lat is not None:
                from shapely.geometry import Point

                mass_point = Point(mass_lon, mass_lat)  # Point expects (x=lon, y=lat)
                nearest_pois, distances = index.get_nearest(1, mass_point)

                logger.debug(
                    f"Nearest POI: {nearest_pois[0]}" if nearest_pois else "None",
                    extra={"icon": "⭐"},
                )

                # Create bounding circle; the geocluster performs outlier removal,
                # so we use the original cluster coordinates
                cluster_envelope = shapely.MultiPoint(cluster_coords).convex_hull

                if nearest_pois and shapely.Point(nearest_pois[0].coords).intersects(
                    cluster_envelope,
                ):
                    poi = nearest_pois[0]
                    pwpt = gpxpy.gpx.GPXWaypoint(
                        latitude=poi.coords[1],
                        longitude=poi.coords[0],
                        name=poi.name,
                        description=f"{poi.description} ({poi.rank})",
                        symbol="cluster-poi",
                    )
                    self.__gpx_out.waypoints.append(pwpt)
            del index

    def __add_journal_markers(self) -> None:
        for asset, asset_type in self.__db.get_assets_by_date(
            str(self.__date),  # FIXME: Inconsistent types
            ("markdown", "audio"),
        ):
            geo = self.__db.get_geo_by_name(asset)
            if geo is None:
                continue
            metadata = self.__db.get_metadata(asset)
            # geo dict uses separate latitude/longitude keys - GPX format (lat, lon)
            # Convert latitude/longitude to float if they're strings
            latitude = geo["latitude"]
            longitude = geo["longitude"]
            assert type(latitude) in (float, int), (
                f"Invalid latitude type: {type(latitude)}"
            )
            assert type(longitude) in (float, int), (
                f"Invalid longitude type: {type(longitude)}"
            )

            comment = f"{metadata['id']}" if metadata is not None else ""

            wpt = gpxpy.gpx.GPXWaypoint(
                latitude=float(latitude),
                longitude=float(longitude),
                name="Journal Entry",
                comment=comment,
                symbol=f"{asset_type}-journal-entry",
            )
            self.__gpx_out.waypoints.append(wpt)

    def to_xml(self) -> str:
        return self.__gpx_out.to_xml()
