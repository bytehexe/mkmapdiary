from copy import deepcopy
import requests
import shapely
import json
from mkmapdiary.poiIndexBuilder import PoiIndexBuilder


class PoiIndex:
    def __init__(self, geo_data):
        geo_data = deepcopy(geo_data)

        # TODO: Check for areas already indexed

        # Get the region index
        response = requests.get("https://download.geofabrik.de/index-v1.json")
        self.geofabrik_data = response.json()

        # Find best matching regions
        regions = []
        while geo_data.is_empty is False:
            print("Next iteration to find best matching Geofabrik region...")
            best_region = self.__findBestRegion(geo_data)
            if best_region is None:
                break
            regions.append(best_region)
            print(f"Selected region: {best_region['name']}")
            geo_data = best_region["remaining_geo_data"]

        print("Selected Geofabrik regions for POI extraction:")
        for region in regions:
            print(f" - {region['name']}")

        for region in regions:
            PoiIndexBuilder(region).build_index()

    def __findBestRegion(self, geo_data):

        best = None

        for region in self.geofabrik_data["features"]:

            # Check if any of the provided geo_data areas intersect with the region
            shape = shapely.from_geojson(json.dumps(region))
            remaining_geo_data = shapely.difference(geo_data, shape)
            if remaining_geo_data.equals(geo_data):
                continue  # No intersection

            remaining_area = shapely.area(remaining_geo_data)

            if best is None or remaining_area < best["remaining_area"]:
                best = dict(
                    id=region["properties"]["id"],
                    name=region["properties"]["name"],
                    url=region["properties"]["urls"]["pbf"],
                    remaining_geo_data=remaining_geo_data,
                    remaining_area=remaining_area,
                )

        return best


if __name__ == "__main__":
    # use Berlin as test point
    berlin_geo_data = shapely.Point(13.4050, 52.5200).buffer(0.1)
    poi_index = PoiIndex(berlin_geo_data)
