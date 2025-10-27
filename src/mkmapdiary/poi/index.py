import logging
import pathlib
from threading import Lock
from typing import Optional

import msgpack
import numpy as np
import requests
import shapely
import yaml
from sklearn.metrics.pairwise import haversine_distances
from sklearn.neighbors import BallTree

from mkmapdiary.poi.ballTreeBuilder import BallTreeBuilder
from mkmapdiary.poi.indexBuilder import IndexBuilder, Region
from mkmapdiary.poi.indexFileReader import IndexFileReader
from mkmapdiary.poi.regionFinder import RegionFinder
from mkmapdiary.util.osm import calculate_rank, clip_rank
from mkmapdiary.util.projection import LocalProjection

logger = logging.getLogger(__name__)

lock = Lock()


class Index:
    def __init__(self, geo_data, keep_pbf: bool = False, rank_offset=(-1, 1)):
        with lock:
            self.__init(geo_data, keep_pbf, rank_offset)

    def __init(self, geo_data, keep_pbf: bool, rank_offset):

        with open(
            pathlib.Path(__file__).parent.parent
            / "resources"
            / "poi_filter_config.yaml"
        ) as config_file:
            self.filter_config = yaml.safe_load(config_file)

        # Get the region index
        response = requests.get("https://download.geofabrik.de/index-v1.json")
        self.geofabrik_data = response.json()

        # Find best matching regions
        finder = RegionFinder(geo_data, self.geofabrik_data)
        regions = finder.find_regions()

        for region in regions:
            poi_index_path = (
                pathlib.Path.home()
                / ".mkmapdiary"
                / "cache"
                / "poi_index"
                / f"{region.id}.idx"
            )

            if not poi_index_path.exists():
                logger.info(
                    f"POI index for region {region.name} does not exist. Building..."
                )
                IndexBuilder(region, keep_pbf=keep_pbf).build_index()
                continue

            region_index = IndexFileReader(poi_index_path)
            if not region_index.is_up_to_date(31536000):
                logger.info(
                    f"POI index for region {region.name} is outdated. Rebuilding..."
                )
                IndexBuilder(region, keep_pbf=keep_pbf).build_index()
                continue
            if not region_index.is_valid(self.filter_config):
                logger.info(
                    f"POI index for region {region.name} is invalid. Rebuilding..."
                )
                IndexBuilder(region, keep_pbf=keep_pbf).build_index()
                continue

            logger.info(f"Using existing POI index for region {region.name}.")

        local_projection = LocalProjection(geo_data)
        local_geo_data = local_projection.to_local(geo_data)

        if local_geo_data.area == 0:
            local_geo_data = local_geo_data.buffer(50)

        self.bounding_radius = shapely.minimum_bounding_radius(local_geo_data)
        self.center = local_projection.to_wgs(
            shapely.centroid(local_projection.to_local(geo_data))
        )

        if geo_data.area == 0:
            raise ValueError(
                "Invalid bounding radius calculated for the area of interest."
            )
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
            poi_index_path = (
                pathlib.Path.home()
                / ".mkmapdiary"
                / "cache"
                / "poi_index"
                / f"{region.id}.idx"
            )

            reader = IndexFileReader(poi_index_path)
            data = reader.read()
            builder.load(data, min_rank, max_rank)

        logger.info("Generating ball tree ...")
        self.ball_tree = builder.build()

    def get_all(self):
        logger.info("Querying ball tree ...")
        logger.debug("Bounding radius (meters): %s", self.bounding_radius)
        logger.debug("Center coordinates (WGS): %s", self.center)
        # Convert from Shapely Point (x=lon, y=lat) to BallTree expected (lat, lon) format
        return self.ball_tree.query_radius(
            [self.center.y, self.center.x],
            r=self.bounding_radius,
        )

    def get_nearest(self, n: int, point: Optional[shapely.Point] = None):
        if point is None:
            point = self.center

        logger.info("Querying ball tree for nearest neighbors ...")
        logger.debug("Center coordinates (WGS): %s", self.center)
        # Convert from Shapely Point (x=lon, y=lat) to BallTree expected (lat, lon) format
        return self.ball_tree.query(
            [point.y, point.x],  # type: ignore
            k=n,
        )


if __name__ == "__main__":
    # use Berlin as test point - Point constructor uses (x=lon, y=lat) format
    berlin_center = shapely.Point(13.4050, 52.5200)  # (lon, lat)
    projection = LocalProjection(berlin_center)
    berlin_geo_data = projection.to_wgs(
        projection.to_local(berlin_center).buffer(60000)
    )
    poi_index = Index(berlin_geo_data, keep_pbf=True)
    for idx in sorted(poi_index.get_all(), key=lambda x: -x.rank):
        print(f"POI: {idx.name}; {idx.coords}, rank {idx.rank}")

    for poi, distance in list(zip(*poi_index.get_nearest(1))):
        print(
            f"Nearest POI: {poi.name}; {poi.coords}, distance {distance:.2f} m, rank {poi.rank}"
        )
