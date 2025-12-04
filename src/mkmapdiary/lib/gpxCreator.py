import logging
import warnings
from collections import defaultdict
from collections.abc import Sequence
from pathlib import Path, PosixPath
from typing import Any

import gpxpy
import gpxpy.gpx
import hdbscan
import numpy as np
import shapely
from shapely.geometry import Point
from whenever import Date, Instant

from mkmapdiary.lib.assetRegistry import AssetRegistry
from mkmapdiary.lib.geoCluster import GeoCluster
from mkmapdiary.lib.statistics import Statistics
from mkmapdiary.poi.index import Index, IndexKey
from mkmapdiary.util.log import ThisMayTakeAWhile
from mkmapdiary.util.projection import LocalProjection

logger = logging.getLogger(__name__)


class GpxCreator:
    def __init__(
        self,
        index_data: dict[str, Any],
        sources: Sequence[str | PosixPath],
        db: AssetRegistry,
        region_cache_dir: Path,
        priorities: dict[str, int | None],
        skip_poi_detection: bool = False,
        simplification_tolerance: float = 0.0,
    ) -> None:
        self.__sources = sources
        self.__db = db
        self.__region_cache_dir = region_cache_dir
        self.__priorities = priorities
        self.index_data = index_data
        self.__skip_poi_detection = skip_poi_detection
        self.__simplification_tolerance = simplification_tolerance

        # Data structures organized by date - using defaultdict for lazy initialization
        self.__coords_by_date: defaultdict[Date, list[list[float]]] = defaultdict(list)
        self.__gpx_data_by_date: defaultdict[Date, dict[str, Any]] = defaultdict(
            lambda: {"waypoints": [], "tracks": [], "routes": []}
        )
        self.__statistics_by_date: defaultdict[Date, Statistics] = defaultdict(
            Statistics
        )

        self.index = Index(self.index_data, self.__region_cache_dir, keep_pbf=True)

        self.__init()

    def __init(self) -> None:
        logger.debug(
            "Creating GPX creator - dates will be discovered during processing..."
        )

        with ThisMayTakeAWhile(logger, "Parsing GPX sources"):
            for source in self.__sources:
                self.__load_source(source)
        with ThisMayTakeAWhile(logger, "Computing clusters"):
            self.__compute_clusters()
        self.__add_journal_markers()

        logger.debug(
            f"Processed GPX data for dates: {sorted(self.get_available_dates())}"
        )

    def __load_source(self, source: str | PosixPath) -> None:
        logger.debug(f"Loading GPX source: {source}")
        with open(source, encoding="utf-8") as f:
            gpx = gpxpy.parse(f)

        # Process waypoints
        for mwpt in gpx.waypoints:
            if mwpt.time is not None:
                pt_date = Date.from_py_date(mwpt.time.date())
                # defaultdict will automatically create the entry if it doesn't exist
                self.__gpx_data_by_date[pt_date]["waypoints"].append(mwpt)

        # Process tracks
        for trk in gpx.tracks:
            # Group track segments by date
            segments_by_date: dict[Date, list[gpxpy.gpx.GPXTrackSegment]] = {}

            for seg in trk.segments:
                track_points_by_date: dict[Date, list[gpxpy.gpx.GPXTrackPoint]] = {}

                last_time = Instant.MAX
                for pt in seg.points:
                    if pt.time is not None:
                        pt_time = Instant.from_py_datetime(pt.time)
                        pt_date = Date.from_py_date(pt.time.date())
                        if last_time == Instant.MAX:
                            self.__statistics_by_date[pt_date].reset()

                        self.__statistics_by_date[pt_date].add_entry(
                            pt_time,
                            (pt.longitude, pt.latitude),
                            pt.elevation,
                        )
                        # defaultdict will automatically create the entry if it doesn't exist
                        if pt_date not in track_points_by_date:
                            track_points_by_date[pt_date] = []
                        track_points_by_date[pt_date].append(pt)

                        # Store coordinates as (lon, lat) for consistent interface format
                        # Converting from GPX format (lat, lon) to interface format (lon, lat)
                        time_diff = max(
                            int(round((pt_time - last_time).in_seconds())), 1
                        )
                        self.__coords_by_date[pt_date].extend(
                            [[pt.longitude, pt.latitude]] * time_diff
                        )
                        last_time = pt_time

                # Create segments for each date
                for pt_date, points in track_points_by_date.items():
                    new_seg = gpxpy.gpx.GPXTrackSegment()
                    for point in points:
                        new_seg.points.append(point)

                    if pt_date not in segments_by_date:
                        segments_by_date[pt_date] = []
                    segments_by_date[pt_date].append(new_seg)

            # Create tracks for each date
            for pt_date, segments in segments_by_date.items():
                new_trk = gpxpy.gpx.GPXTrack(name=trk.name, description=trk.description)
                for segment in segments:
                    new_trk.segments.append(segment)
                self.__gpx_data_by_date[pt_date]["tracks"].append(new_trk)

        # Process routes
        for rte in gpx.routes:
            route_points_by_date: dict[Date, list[gpxpy.gpx.GPXRoutePoint]] = {}

            for rte_pt in rte.points:
                if rte_pt.time is not None:
                    pt_date = Date.from_py_date(rte_pt.time.date())
                    # defaultdict will automatically create the entry if it doesn't exist
                    if pt_date not in route_points_by_date:
                        route_points_by_date[pt_date] = []
                    route_points_by_date[pt_date].append(rte_pt)

            # Create routes for each date
            for pt_date, points in route_points_by_date.items():  # type: ignore
                new_rte = gpxpy.gpx.GPXRoute(name=rte.name, description=rte.description)
                for point in points:
                    new_rte.points.append(point)  # type: ignore
                self.__gpx_data_by_date[pt_date]["routes"].append(new_rte)

    def __compute_clusters(self) -> None:
        logger.debug("Computing geospatial clusters for all dates")

        if self.__skip_poi_detection:
            logger.info(
                "Skipping POI detection as per configuration",
                extra={"icon": "⏭️"},
            )
            return

        # First pass: compute all clusters and their index keys
        all_clusters = []

        for date in self.__coords_by_date.keys():
            clusters_for_date = self.__compute_clusters_for_date(date)
            all_clusters.extend(clusters_for_date)

        # Sort clusters by index key to group similar ones together
        all_clusters.sort(key=lambda x: x["index_key"])

        # Second pass: process clusters in index key order for optimal performance
        logger.debug(f"Processing {len(all_clusters)} clusters grouped by index key")
        self.__process_sorted_clusters(all_clusters)

    def __compute_clusters_for_date(self, date: Date) -> list[dict]:
        """Compute clusters for a date and return cluster data with index keys."""
        logger.debug(f"Computing geospatial clusters for date {date}")
        coords = self.__coords_by_date[date]
        if len(coords) < 10:
            return []

        coords_array = np.array(coords)

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
            clusterer.fit(np.radians(coords_array))

        # Create index once to get index keys for all clusters in this date
        index = self.index
        clusters_data = []

        labels = clusterer.labels_
        for label in set(labels):
            if label == -1:
                continue
            cluster_coords = coords_array[labels == label]

            # Convert to list of tuples for GeoCluster
            cluster_coords_list = [
                (float(coord[0]), float(coord[1])) for coord in cluster_coords
            ]
            cluster = GeoCluster(cluster_coords_list)

            if cluster.radius > 1200:
                # Ignore overly large clusters
                continue

            if cluster.shape.is_empty:
                continue

            # Get index key for this cluster
            logger.debug(f"Getting index key for cluster {label} on date {date}")
            key = index.get_key(cluster.shape)

            # Store cluster data for later processing
            cluster_data = {
                "date": date,
                "label": label,
                "cluster": cluster,
                "cluster_coords": cluster_coords,
                "index_key": key,
            }
            clusters_data.append(cluster_data)

        logger.debug(f"Found {len(clusters_data)} valid clusters for date {date}")
        return clusters_data

    def __process_sorted_clusters(self, all_clusters: list[dict]) -> None:
        """Process clusters sorted by index key for optimal performance."""
        index = self.index
        current_proxy = None

        for cluster_data in all_clusters:
            date: Date = cluster_data["date"]
            label: int = cluster_data["label"]
            cluster: GeoCluster = cluster_data["cluster"]
            cluster_coords: list[tuple[float, float]] = cluster_data["cluster_coords"]
            key: IndexKey = cluster_data["index_key"]

            # Add basic cluster waypoints first
            # cluster.mass_point returns (lon, lat) format, convert for GPX which expects (lat, lon)
            mlon, mlat = cluster.mass_point
            mwpt = gpxpy.gpx.GPXWaypoint(
                latitude=mlat,
                longitude=mlon,
                name=f"Cluster {label}",
                description=f"Cluster of {len(cluster_coords)} points and radius {cluster.radius:.1f} m",
                symbol="mkmapdiary|cluster-mass",
            )
            self.__gpx_data_by_date[date]["waypoints"].append(mwpt)

            # cluster.midpoint returns (lon, lat) format, convert for GPX which expects (lat, lon)
            clon, clat = cluster.midpoint
            cwpt = gpxpy.gpx.GPXWaypoint(
                latitude=clat,
                longitude=clon,
                name=f"Cluster {label} Center",
                description=f"Center of cluster {label}",
                symbol="mkmapdiary|cluster-center",
                position_dilution=cluster.radius,
            )
            self.__gpx_data_by_date[date]["waypoints"].append(cwpt)

            # Add a POI for each cluster center
            logger.info(
                f"Searching POIs near cluster {label} at {clat},{clon} for date {date}",
                extra={"icon": "📍"},
            )

            # Load regions with potential reuse of existing proxy
            logger.debug("Loading regions (with potential reuse of existing proxy)")
            proxy = index.load_regions(key, existing_proxy=current_proxy)
            current_proxy = proxy  # Store for potential reuse in next clusters

            logger.debug("Index proxy loaded, querying nearest POI")
            # Convert mass_point (lon, lat) to shapely.Point for proxy.get_nearest
            mass_lon, mass_lat = cluster.mass_point
            if mass_lon is not None and mass_lat is not None:
                logger.debug("Get nearest POI to cluster mass point")
                mass_point = Point(mass_lon, mass_lat)  # Point expects (x=lon, y=lat)

                # Create convex hull and bounding circle; the geocluster performs outlier removal,
                # so we use the original cluster coordinates
                logger.debug("Creating cluster envelope for POI intersection test")
                cluster_envelope = shapely.MultiPoint(cluster_coords).convex_hull
                local_projection = LocalProjection(mass_point)
                local_envelope = local_projection.to_local(cluster_envelope)
                local_bounding_circle = shapely.minimum_bounding_circle(local_envelope)
                local_center = local_bounding_circle.centroid
                radius = local_bounding_circle.boundary.distance(local_center)
                center = local_projection.to_wgs(local_center)
                local_mass_point = local_projection.to_local(mass_point)

                nearby_pois = proxy.get_within_radius(radius, center)
                nearby_pois = [
                    poi
                    for poi in nearby_pois
                    if self.__priorities.get(poi.symbol, 0) is not None
                ]

                nearby_pois.sort(
                    key=lambda poi: (
                        -(self.__priorities.get(poi.symbol, 0) or 0),
                        local_projection.to_local(
                            Point(poi.coords[0], poi.coords[1])
                        ).distance(local_mass_point),
                    )
                )

                for poi in nearby_pois:
                    logger.debug(
                        f"Nearest POI: {poi}" if nearby_pois else "None",
                        extra={"icon": "⭐"},
                    )

                    logger.debug("Testing POI intersection with cluster envelope")
                    pwpt = gpxpy.gpx.GPXWaypoint(
                        latitude=poi.coords[1],
                        longitude=poi.coords[0],
                        name=poi.name,
                        description=f"{poi.description} ({poi.rank})",
                        symbol=f"mkmapdiary|poi|{poi.symbol}",
                    )
                    self.__gpx_data_by_date[date]["waypoints"].append(pwpt)
                    break  # Only add the highest priority POI

    def __add_journal_markers(self) -> None:
        logger.debug("Adding journal markers for all dates")

        # Add journal markers for geotagged journal dates
        for date in self.__db.get_geotagged_journal_dates():
            self.__add_journal_markers_for_date(date)

    def __add_journal_markers_for_date(self, date: Date) -> None:
        logger.debug(f"Adding journal markers for date {date}")
        for asset in self.__db.get_assets_by_date(
            date,
            ("markdown", "audio"),
        ):
            geo_asset = self.__db.get_geotagged_asset_by_path(asset.path)
            if geo_asset is None:
                continue
            # geo asset uses latitude/longitude properties - GPX format (lat, lon)
            # Convert latitude/longitude to float if they're strings
            latitude = geo_asset.latitude
            longitude = geo_asset.longitude
            assert latitude is not None and longitude is not None, (
                "Geotagged asset must have valid coordinates"
            )
            assert type(latitude) in (float, int), (
                f"Invalid latitude type: {type(latitude)}"
            )
            assert type(longitude) in (float, int), (
                f"Invalid longitude type: {type(longitude)}"
            )

            comment = f"{geo_asset.id}" if geo_asset.id is not None else ""

            wpt = gpxpy.gpx.GPXWaypoint(
                latitude=float(latitude),
                longitude=float(longitude),
                name="Journal Entry",
                comment=comment,
                symbol=f"mkmapdiary|{asset.type}-journal-entry",
            )
            self.__gpx_data_by_date[date]["waypoints"].append(wpt)

    def to_xml(self, date: Date) -> str:
        """Generate GPX XML for a specific date."""
        if date not in self.__gpx_data_by_date:
            raise ValueError(
                f"Date {date} was not processed by this GpxCreator instance"
            )

        # Create a new GPX object for this date
        gpx_out = gpxpy.gpx.GPX()

        # Add waypoints for this date
        for waypoint in self.__gpx_data_by_date[date]["waypoints"]:
            gpx_out.waypoints.append(waypoint)

        # Add tracks for this date
        for track in self.__gpx_data_by_date[date]["tracks"]:
            # Apply simplification to each track segment if tolerance > 0
            if self.__simplification_tolerance > 0:
                for segment in track.segments:
                    segment.simplify(max_distance=self.__simplification_tolerance)
            gpx_out.tracks.append(track)

        # Add routes for this date
        for route in self.__gpx_data_by_date[date]["routes"]:
            gpx_out.routes.append(route)

        return gpx_out.to_xml()

    def get_available_dates(self) -> set[Date]:
        """Return all dates that are available in this GpxCreator instance."""
        return set(self.__gpx_data_by_date.keys())

    def get_statistics(self) -> dict[Date, Statistics]:
        """Return statistics for all dates processed by this GpxCreator instance."""
        return dict(self.__statistics_by_date)
