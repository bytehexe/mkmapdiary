from copy import deepcopy
import requests
import shapely
import json
from mkmapdiary.poi.indexBuilder import IndexBuilder, Region
from mkmapdiary.util.osm import calculate_rank, clip_rank
from mkmapdiary.util.projection import LocalProjection
from mkmapdiary.poi.indexFileReader import IndexFileReader
from mkmapdiary.poi.ballTreeBuilder import BallTreeBuilder
from typing import List, Optional, Tuple, Any
import msgpack
import pathlib
from sklearn.neighbors import BallTree
from sklearn.metrics.pairwise import haversine_distances
import numpy as np

from collections import namedtuple
import yaml
from threading import Lock
import sys

lock = Lock()


class Index:
    def __init__(self, geo_data, keep_pbf: bool = False, rank_offset=(-1, 1)):
        with lock:
            self.__init(geo_data, keep_pbf, rank_offset)

    def __init(self, geo_data, keep_pbf: bool, rank_offset):
        geo_data_copy = deepcopy(geo_data)

        # TODO: Check for areas already indexed

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
        regions: List[Region] = []
        sys.stderr.write("Finding best matching Geofabrik regions...\n")
        sys.stderr.flush()
        while geo_data_copy.is_empty is False:
            sys.stderr.write(
                "Next iteration to find best matching Geofabrik region...\n"
            )
            sys.stderr.flush()
            best_region, remaining_geo_data = self.__findBestRegion(
                geo_data_copy, regions
            )
            if best_region is None:
                break
            regions.append(best_region)
            sys.stderr.write(f"Selected region: {best_region.name}\n")
            sys.stderr.flush()
            geo_data_copy = remaining_geo_data
        sys.stderr.write("Selected Geofabrik regions for POI extraction:\n")
        sys.stderr.flush()
        for region in regions:
            sys.stderr.write(f" - {region.name}\n")
            sys.stderr.flush()

        for region in regions:
            poi_index_path = (
                pathlib.Path.home()
                / ".mkmapdiary"
                / "cache"
                / "poi_index"
                / f"{region.id}.idx"
            )

            if not poi_index_path.exists():
                sys.stderr.write(
                    f"POI index for region {region.name} does not exist. Building...\n"
                )
                sys.stderr.flush()
                IndexBuilder(region, keep_pbf=keep_pbf).build_index()
                continue

            region_index = IndexFileReader(poi_index_path)
            if not region_index.is_up_to_date(31536000):
                sys.stderr.write(
                    f"POI index for region {region.name} is outdated. Rebuilding...\n"
                )
                sys.stderr.flush()
                IndexBuilder(region, keep_pbf=keep_pbf).build_index()
                continue
            if not region_index.is_valid(self.filter_config):
                sys.stderr.write(
                    f"POI index for region {region.name} is invalid. Rebuilding...\n"
                )
                sys.stderr.flush()
                IndexBuilder(region, keep_pbf=keep_pbf).build_index()
                continue

            sys.stderr.write(f"Using existing POI index for region {region.name}.\n")
            sys.stderr.flush()

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
        sys.stderr.write(f"Calculated rank for the area of interest: {rank}\n")
        sys.stderr.flush()

        if rank is None:
            raise ValueError("Invalid rank calculated for the area of interest.")

        min_rank = clip_rank(rank + rank_offset[0])
        max_rank = clip_rank(rank + rank_offset[1])

        builder = BallTreeBuilder(self.filter_config)

        for region in regions:
            sys.stderr.write(f"Loading POI index for region: {region.name}\n")
            sys.stderr.flush()
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

        sys.stderr.write("Generating ball tree ...\n")
        sys.stderr.flush()
        self.ball_tree = builder.build()

    def get_all(self):
        print("Querying ball tree ...")
        print("Bounding radius (meters):", self.bounding_radius)
        print("Center coordinates (WGS):", self.center)
        # Convert from Shapely Point (x=lon, y=lat) to BallTree expected (lat, lon) format
        return self.ball_tree.query_radius(
            [self.center.y, self.center.x],
            r=self.bounding_radius,
        )

    def get_nearest(self, n: int, point: Optional[shapely.Point] = None):
        if point is None:
            point = self.center

        print("Querying ball tree for nearest neighbors ...")
        print("Center coordinates (WGS):", self.center)
        # Convert from Shapely Point (x=lon, y=lat) to BallTree expected (lat, lon) format
        return self.ball_tree.query(
            [point.y, point.x],
            k=n,
        )

    def __findBestRegion(self, geo_data, used_regions) -> Tuple[Optional[Region], Any]:

        best = None
        remaining_geo_data = geo_data
        best_size = float("inf")

        for region in self.geofabrik_data["features"]:

            if any(r.id == region["properties"]["id"] for r in used_regions):
                continue  # Skip already used regions

            # Check if any of the provided geo_data areas intersect with the region
            shape = shapely.from_geojson(json.dumps(region))
            remaining_geo_data = shapely.difference(geo_data, shape)
            if remaining_geo_data.equals(geo_data):
                continue  # No intersection

            size = shapely.area(
                geo_data
            )  # Note: size is only an approximation, not meaningful due to projections

            if best is None or size < best_size:
                best = Region(
                    id=region["properties"]["id"],
                    name=region["properties"]["name"],
                    url=region["properties"]["urls"]["pbf"],
                )

        return best, remaining_geo_data


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
