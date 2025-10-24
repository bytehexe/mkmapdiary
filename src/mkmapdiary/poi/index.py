from copy import deepcopy
import requests
import shapely
import json
from mkmapdiary.poi.indexBuilder import IndexBuilder, Region
from mkmapdiary.util.osm import calculate_rank, clip_rank
from mkmapdiary.util.projection import LocalProjection
from mkmapdiary.poi.indexFileReader import IndexFileReader
from mkmapdiary.poi.ballTreeBuilder import BallTreeBuilder
from typing import List, Optional, Any
import msgpack
import pathlib
from sklearn.neighbors import BallTree
from sklearn.metrics.pairwise import haversine_distances
import numpy as np

from collections import namedtuple
import yaml
from threading import Lock

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
        while geo_data_copy.is_empty is False:
            print("Next iteration to find best matching Geofabrik region...")
            best_region = self.__findBestRegion(geo_data_copy)
            if best_region is None:
                break
            regions.append(best_region)
            print(f"Selected region: {best_region.name}")
            geo_data_copy = best_region.remaining_geo_data

        print("Selected Geofabrik regions for POI extraction:")
        for region in regions:
            print(f" - {region.name}")

        for region in regions:
            poi_index_path = (
                pathlib.Path.home()
                / ".mkmapdiary"
                / "cache"
                / "poi_index"
                / f"{region.id}.idx"
            )

            if not poi_index_path.exists():
                print(f"POI index for region {region.name} does not exist. Building...")
                IndexBuilder(region, keep_pbf=keep_pbf).build_index()
                continue

            region_index = IndexFileReader(poi_index_path)
            if not region_index.is_up_to_date(31536000):
                print(f"POI index for region {region.name} is outdated. Rebuilding...")
                IndexBuilder(region, keep_pbf=keep_pbf).build_index()
                continue
            if not region_index.is_valid(self.filter_config):
                print(f"POI index for region {region.name} is invalid. Rebuilding...")
                IndexBuilder(region, keep_pbf=keep_pbf).build_index()
                continue

            print(f"Using existing POI index for region {region.name}.")

        if geo_data.area > 0:
            local_projection = LocalProjection(geo_data)
            self.bounding_radius = shapely.minimum_bounding_radius(
                local_projection.to_local(geo_data)
            )
            self.center = local_projection.to_wgs(
                shapely.centroid(local_projection.to_local(geo_data))
            )
        else:
            raise ValueError(
                "Invalid bounding radius calculated for the area of interest."
            )
        rank = calculate_rank(None, self.bounding_radius)
        print(f"Calculated rank for the area of interest: {rank}")

        if rank is None:
            raise ValueError("Invalid rank calculated for the area of interest.")

        min_rank = clip_rank(rank + rank_offset[0])
        max_rank = clip_rank(rank + rank_offset[1])

        builder = BallTreeBuilder(self.filter_config)

        for region in regions:
            print(f"Loading POI index for region: {region.name}")
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

        print("Generating ball tree ...")
        self.ball_tree = builder.build()

    def get_all(self):
        print("Querying ball tree ...")
        print("Bounding radius (meters):", self.bounding_radius)
        print("Center coordinates (WGS):", self.center)
        return self.ball_tree.query_radius(
            [self.center.y, self.center.x],
            r=self.bounding_radius,
        )

    def get_nearest(self, n: int, point: Optional[shapely.Point] = None):
        if point is None:
            point = self.center

        print("Querying ball tree for nearest neighbors ...")
        print("Center coordinates (WGS):", self.center)
        return self.ball_tree.query(
            [point.y, point.x],
            k=n,
        )

    def __findBestRegion(self, geo_data) -> Optional[Region]:

        best = None

        for region in self.geofabrik_data["features"]:

            # Check if any of the provided geo_data areas intersect with the region
            shape = shapely.from_geojson(json.dumps(region))
            remaining_geo_data = shapely.difference(geo_data, shape)
            if remaining_geo_data.equals(geo_data):
                continue  # No intersection

            remaining_area = shapely.area(remaining_geo_data)

            if best is None or remaining_area < best.remaining_area:
                best = Region(
                    id=region["properties"]["id"],
                    name=region["properties"]["name"],
                    url=region["properties"]["urls"]["pbf"],
                    remaining_geo_data=remaining_geo_data,
                    remaining_area=remaining_area,
                )

        return best


if __name__ == "__main__":
    # use Berlin as test point
    berlin_center = shapely.Point(13.4050, 52.5200)
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
