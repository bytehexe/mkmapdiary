from copy import deepcopy
import requests
import shapely
import json
import tempfile
import pyrosm
import yaml
import pathlib
import warnings
import pandas.errors


class PoiIndex:
    def __init__(self, geo_data):
        geo_data = deepcopy(geo_data)

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
            self.__buildPoiIndex(region)

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

    def __create_custom_filter(self, filter_config):
        custom_filter = {}
        for entry in filter_config:
            filters = entry.get("filters", [])
            for filter in filters:
                for key, value in filter.items():
                    if value is True:
                        custom_filter[key] = True
                        continue
                    if key not in custom_filter:
                        custom_filter[key] = set()
                    if custom_filter[key] is not True:
                        custom_filter[key].add(value)

        for key, value in custom_filter.items():
            if value is not True:
                custom_filter[key] = list(value)

        return custom_filter

    def __filter_pois(self, pois, filter_config):
        for entry in filter_config:
            symbol = entry.get("symbol", "unknown")
            filters = entry.get("filters", [])
            for filter in filters:
                try:
                    filter_expression = None
                    for key, value in filter.items():
                        if value is True:
                            new_filter = pois[key].notnull()
                        else:
                            new_filter = pois[key] == value
                        if filter_expression is None:
                            filter_expression = new_filter
                        else:
                            filter_expression = filter_expression & new_filter

                    results = pois[filter_expression]
                    count = results.shape[0]
                    print(f"{symbol} ({filter}):", count)
                    yield results, symbol, filter
                except KeyError as e:
                    print(f"{symbol} ({filter}): 0 (key not found: {e})")
                    continue

                pois = pois[~filter_expression]

    def __buildPoiIndex(self, region):
        print(f"Building POI index for region: {region['name']}")
        result = requests.get(region["url"])
        with tempfile.NamedTemporaryFile(suffix=".pbf") as temp_file:
            temp_file.write(result.content)
            temp_file.flush()

            # Load filter configuration
            filter_config_file = (
                pathlib.Path(__file__).parent / "extras" / "poi_filter_config.yaml"
            )
            with open(filter_config_file, "r") as f:
                filter_config = yaml.safe_load(f)
            custom_filter = self.__create_custom_filter(filter_config)

            # Load OSM data
            osm = pyrosm.OSM(temp_file.name)

            with warnings.catch_warnings():
                warnings.simplefilter(
                    action="ignore", category=pandas.errors.PerformanceWarning
                )
                pois = osm.get_pois(custom_filter=custom_filter)

            pois = self.__filter_pois(pois, filter_config)
            for poi_group, symbol, filter in pois:

                # Process each poi_group as needed
                print(
                    f"Processing {len(poi_group)} POIs for symbol {symbol} and filter {filter}"
                )


if __name__ == "__main__":
    # use Berlin as test point
    berlin_geo_data = shapely.Point(13.4050, 52.5200).buffer(0.1)
    poi_index = PoiIndex(berlin_geo_data)
