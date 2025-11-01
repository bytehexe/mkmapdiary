import logging
import pathlib
from threading import Lock
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import requests
import shapely
import yaml

from mkmapdiary.poi.ballTreeBuilder import BallTreeBuilder
from mkmapdiary.poi.indexBuilder import IndexBuilder
from mkmapdiary.poi.indexFileReader import IndexFileReader
from mkmapdiary.poi.regionFinder import RegionFinder
from mkmapdiary.util.osm import calculate_rank, clip_rank
from mkmapdiary.util.projection import LocalProjection

logger = logging.getLogger(__name__)

lock = Lock()


class Index:
    def __init__(
        self,
        geo_data: Dict[str, Any],
        cache_dir: pathlib.Path,
        keep_pbf: bool = False,
        rank_offset: Tuple[int, int] = (-1, 1),
    ):
        with lock:
            self.__init(geo_data, cache_dir, keep_pbf, rank_offset)

    def __init(
        self,
        geo_data: Dict[str, Any],
        cache_dir: pathlib.Path,
        keep_pbf: bool,
        rank_offset: Tuple[int, int],
    ) -> None:
        with open(
            pathlib.Path(__file__).parent.parent
            / "resources"
            / "poi_filter_config.yaml",
        ) as config_file:
            self.filter_config = yaml.safe_load(config_file)

        # Get the region index
        response = requests.get("https://download.geofabrik.de/index-v1.json")
        self.geofabrik_data = response.json()

        # Find best matching regions
        finder = RegionFinder(geo_data, self.geofabrik_data)
        regions = finder.find_regions()

        for region in regions:
            poi_index_path = cache_dir / f"{region.id}.idx"

            if not poi_index_path.exists():
                logger.info(
                    f"POI index for region {region.name} does not exist. Building...",
                )
                IndexBuilder(region, cache_dir, keep_pbf=keep_pbf).build_index()
                continue

            region_index = IndexFileReader(poi_index_path)
            if not region_index.is_up_to_date(31536000):
                logger.info(
                    f"POI index for region {region.name} is outdated. Rebuilding...",
                )
                IndexBuilder(region, cache_dir, keep_pbf=keep_pbf).build_index()
                continue
            if not region_index.is_valid(self.filter_config):
                logger.info(
                    f"POI index for region {region.name} is invalid. Rebuilding...",
                )
                IndexBuilder(region, cache_dir, keep_pbf=keep_pbf).build_index()
                continue

            logger.info(f"Using existing POI index for region {region.name}.")

        logger.debug("Calculating area of interest parameters...")

        logger.debug("Projecting geo data to local coordinates...")

        local_projection = LocalProjection(geo_data)
        local_geo_data = local_projection.to_local(geo_data)

        logger.debug("Calculating center...")
        self.center = local_projection.to_wgs(
            shapely.centroid(local_projection.to_local(geo_data)),
        )

        logger.debug("Calculating bounding radius...")
        if local_geo_data.area == 0:
            logger.debug(
                "Area is zero, buffering geometry by 50 meters to avoid issues...",
            )
            try:
                # Compute convex hull to simplify geometry before buffering
                # This helps avoid memory issues, otherwise buffering complex geometries can be very expensive
                local_geo_data = local_geo_data.convex_hull
            except Exception as e:
                logger.warning("Error occurred while calculating convex hull: %s", e)
            local_geo_data = local_geo_data.buffer(50, resolution=2, quad_segs=2)

        self.bounding_radius = shapely.minimum_bounding_radius(local_geo_data)

        logger.debug("Calculate rank for area of interest...")
        rank = calculate_rank(None, self.bounding_radius)
        logger.info(f"Calculated rank for the area of interest: {rank}")

        if rank is None:
            raise ValueError("Invalid rank calculated for the area of interest.")

        min_rank = clip_rank(rank + rank_offset[0])
        max_rank = clip_rank(rank + rank_offset[1])

        builder = BallTreeBuilder(self.filter_config)

        for region in regions:
            logger.info(f"Loading POI index for region: {region.name}")
            # Load the index file
            poi_index_path = cache_dir / f"{region.id}.idx"

            reader = IndexFileReader(poi_index_path)
            data = reader.read()
            builder.load(data, min_rank, max_rank)

        logger.debug(f"Index parameters: {regions}, ({min_rank}, {max_rank})")
        logger.info("Generating ball tree ... ")
        self.ball_tree = builder.build()

    def get_all(self) -> List:
        logger.info("Querying ball tree ...")
        logger.debug("Bounding radius (meters): %s", self.bounding_radius)
        logger.debug("Center coordinates (WGS): %s", self.center)
        # Convert from Shapely Point (x=lon, y=lat) to BallTree expected (lat, lon) format
        return self.ball_tree.query_radius(
            np.array([self.center.y, self.center.x]),
            r=self.bounding_radius,
        )

    def get_nearest(
        self, n: int, point: Optional[shapely.Point] = None
    ) -> Tuple[List, List[float]]:
        if point is None:
            point = self.center

        logger.info("Querying ball tree for nearest neighbors ...")
        logger.debug("Center coordinates (WGS): %s", self.center)
        # Convert from Shapely Point (x=lon, y=lat) to BallTree expected (lat, lon) format
        return self.ball_tree.query(
            [point.y, point.x],  # type: ignore
            k=n,
        )
