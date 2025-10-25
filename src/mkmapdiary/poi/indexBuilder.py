import requests
import pathlib
import tempfile
import osmium
import osmium.filter
from ..util import calculate_rank
import shapely
from mkmapdiary.util.projection import LocalProjection
from mkmapdiary.util.osm import MIN_RANK, MAX_RANK
from collections import namedtuple
import msgpack
from typing import IO, Union
from shapely.geometry import shape
from mkmapdiary.poi.indexFileWriter import IndexFileWriter
import yaml
from typing import List, Optional, Any
import sys
import logging

logger = logging.getLogger(__name__)

Region = namedtuple(
    "Region",
    ["id", "name", "url"],
)


class IndexBuilder:
    def __init__(self, region: Region, keep_pbf: bool = False):
        self.region: Region = region
        self.keep_pbf: bool = keep_pbf
        self.cachedir = pathlib.Path.home() / ".mkmapdiary" / "cache" / "poi_index"
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
        logger.info(f"Building POI index for region: {region.name}\n")

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

        logger.info(f"POI index built successfully for region: {region.name}\n")

        return index

    def __downloadPbf(self, region: Region, pbf_file_name: pathlib.Path):
        logger.info(f"Downloading PBF ...\n")
        result = requests.get(region.url)
        result.raise_for_status()
        with open(pbf_file_name, "wb") as pbf_file:
            pbf_file.write(result.content)

    def __buildPoiIndex(self) -> dict:

        logger.info("Building index structure ...")

        index: dict[int, dict[str, list]] = {}
        for i in range(MIN_RANK, MAX_RANK + 1):
            index[i] = {"coords": [], "data": []}

        processor = osmium.FileProcessor(self.pbf_path)
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
                    if all(
                        obj.tags.get(k) == v
                        for k, v in filter_expression.get("tags", {}).items()
                    ):
                        found = True
                        break
                if found:
                    break

            if not found:
                continue

            type_str = obj.type_str()
            poi_id = obj.id

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
                logger.warning(
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
