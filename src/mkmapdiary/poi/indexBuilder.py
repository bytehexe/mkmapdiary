import logging
import pathlib
import sys
import tempfile
from collections import namedtuple

import msgpack
import osmium
import osmium.filter
import requests
import shapely
import yaml
from shapely.geometry import shape

from mkmapdiary.poi.indexFileWriter import IndexFileWriter
from mkmapdiary.util.osm import MAX_RANK, MIN_RANK
from mkmapdiary.util.projection import LocalProjection

from ..util import calculate_rank

logger = logging.getLogger(__name__)

Region = namedtuple(
    "Region",
    ["id", "name", "url"],
)


class IndexBuilder:
    def __init__(self, region: Region, cache_dir: pathlib.Path, keep_pbf: bool = False):
        self.region: Region = region
        self.keep_pbf: bool = keep_pbf
        self.cachedir = cache_dir
        self.cachedir.mkdir(parents=True, exist_ok=True)

        # Open poi_filter_config
        config_path = (
            pathlib.Path(__file__).parent.parent
            / "resources"
            / "poi_filter_config.yaml"
        )
        with open(config_path, "r") as config_file:
            self.filter_config = yaml.safe_load(config_file)

        self.pbf_path = self.cachedir / f"{self.region.id}.pbf"
        self.idx_path = self.cachedir / f"{self.region.id}.idx"

    def build_index(self):
        region = self.region
        logger.info(f"Building POI index for region: {region.name}")

        # Download or use cached PBF file
        if self.pbf_path.exists():
            # No download needed
            index = self.__buildPoiIndex()
        elif self.keep_pbf:
            self.__downloadPbf(region, self.pbf_path)
            index = self.__buildPoiIndex()
        else:
            with tempfile.NamedTemporaryFile(suffix=".pbf") as temp_file:
                path = pathlib.Path(temp_file.name)
                self.__downloadPbf(region, path)
                index = self.__buildPoiIndex()

        # Save the index to a file
        w = IndexFileWriter(self.idx_path, filter_config=self.filter_config)
        w.write(index)

        logger.info(f"POI index built successfully for region: {region.name}")

        return index

    def __downloadPbf(self, region: Region, pbf_file_name: pathlib.Path):
        logger.info(f"Downloading PBF ...")
        result = requests.get(region.url)
        result.raise_for_status()
        with open(pbf_file_name, "wb") as pbf_file:
            pbf_file.write(result.content)

    def __buildPoiIndex(self) -> dict:

        logger.info("Building index structure ...")

        index: dict[int, dict[str, list]] = {}
        for i in range(MIN_RANK, MAX_RANK + 1):
            index[i] = {"coords": [], "data": []}

        all_filters_keys = set()
        for filter_item in self.filter_config:
            for filter_expression in filter_item["filters"]:
                all_filters_keys.update(filter_expression.keys())

        processor = osmium.FileProcessor(self.pbf_path)
        processor.with_filter(osmium.filter.KeyFilter("name"))
        processor.with_filter(osmium.filter.KeyFilter(*all_filters_keys))
        processor.with_locations()
        processor.with_areas()
        processor.with_filter(osmium.filter.GeoInterfaceFilter())

        for obj in processor:
            filter_item_id = None
            filter_expression_id = None

            # Process each POI as needed
            if obj.id is None:
                continue
            poi_name = obj.tags.get("name")
            if poi_name is None:
                continue

            found = False
            for filter_item_id, filter_item in enumerate(self.filter_config):
                for filter_expression_id, filter_expression in enumerate(
                    filter_item["filters"]
                ):
                    poi_tags = obj.tags
                    matches = [
                        (poi_tags.get(k)) if v is True else (poi_tags.get(k) == v)
                        for k, v in filter_expression.items()
                    ]
                    if all(matches):
                        found = True
                        break
                if found:
                    break

            if not found:
                continue

            type_str = obj.type_str()
            poi_id = obj.id

            if poi_id == 3330379812:
                logger.debug("Debug breakpoint")
                logger.debug(f"POI ID: {poi_id}, Name: {poi_name}, Type: {type_str}")
                logger.debug(f"POI Tags: {obj.tags}")
                logger.debug(f"POI filter_item_id: {filter_item_id}")
                logger.debug(f"POI filter_expression_id: {filter_expression_id}")
                logger.debug(f"POI filter_item: {filter_item}")
                logger.debug(f"POI filter_expression: {filter_expression}")
                sys.exit(1)  # Intentional exit for debugging

            if type_str == "n":

                lat = obj.lat  # type: ignore
                lon = obj.lon  # type: ignore
                rank = calculate_rank(place=obj.tags.get("place"))
                radius = None

            else:
                if not hasattr(obj, "__geo_interface__"):
                    continue  # No geometry available

                geom = shape(obj.__geo_interface__["geometry"])  # type: ignore
                proj = LocalProjection(geom)
                local_geom = proj.to_local(geom)
                centroid = proj.to_wgs(local_geom.centroid)
                lat = centroid.y
                lon = centroid.x
                radius = shapely.minimum_bounding_radius(local_geom)
                rank = calculate_rank(radius=radius, place=obj.tags.get("place"))

            if rank is None:
                logger.debug(
                    f"Skipping: {poi_name} (invalid rank); place={obj.tags.get('place', '')}, radius={radius}"
                )
                continue

            assert filter_item_id is not None, "Filter item ID should not be None"
            assert (
                filter_expression_id is not None
            ), "Filter expression ID should not be None"

            index[rank]["coords"].append((lat, lon))
            index[rank]["data"].append(
                (poi_id, poi_name, (filter_item_id, filter_expression_id), rank)
            )

        return index
