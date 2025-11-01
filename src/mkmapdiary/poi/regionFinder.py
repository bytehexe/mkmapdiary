import json
import logging
from copy import deepcopy
from typing import Any, List, Optional, Tuple

import shapely

from mkmapdiary.poi.indexBuilder import Region

logger = logging.getLogger(__name__)


class RegionFinder:
    def __init__(self, geo_data: Any, geofabrik_data: Any) -> None:
        self.geo_data = deepcopy(geo_data)
        self.geofabrik_data = geofabrik_data

    def find_regions(self) -> List[Region]:
        regions: List[Region] = []
        logger.info("Finding best matching Geofabrik regions...")
        while self.geo_data.is_empty is False:
            logger.info("Next iteration to find best matching Geofabrik region...")
            best_region, remaining_geo_data = self._findBestRegion(
                self.geo_data,
                regions,
            )
            if best_region is None:
                break
            self.geo_data = remaining_geo_data

            regions.append(best_region)
            logger.info(f"Selected region: {best_region.name}")
        logger.info("Selected Geofabrik regions for POI extraction:")
        for region in regions:
            logger.info(f" - {region.name}")
        return regions

    def _findBestRegion(
        self, geo_data: Any, used_regions: List[Region]
    ) -> Tuple[Optional[Region], Any]:
        best = None
        remaining_geo_data = geo_data
        return_geo_data = geo_data
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
                shape,
            )  # Note: size is only an approximation, not meaningful due to projections

            if best is None or size < best_size:
                best = Region(
                    id=region["properties"]["id"],
                    name=region["properties"]["name"],
                    url=region["properties"]["urls"]["pbf"],
                )
                best_size = size
                return_geo_data = remaining_geo_data

        return best, return_geo_data
