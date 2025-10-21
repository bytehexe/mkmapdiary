import requests
import pathlib
import tempfile
import yaml
import pyrosm
import warnings
import pandas.errors
from .util import calculate_rank
import shapely
from mkmapdiary.util.projection import LocalProjection


class PoiIndexBuilder:
    def __init__(self, region):
        self.region = region

    def build_index(self):
        index = self.__buildPoiIndex(self.region)
        # TODO: Save or return the index!

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
                    yield results, entry, filter
                except KeyError as e:
                    print(f"{symbol} ({filter}): 0 (key not found: {e})")
                    continue

                pois = pois[~filter_expression]

    def __buildPoiIndex(self, region):
        print(f"Building POI index for region: {region['name']}")

        # TODO: allow caching of pbf files (optional)

        result = requests.get(region["url"])
        with tempfile.NamedTemporaryFile(suffix=".pbf") as temp_file:
            temp_file.write(result.content)
            temp_file.flush()
            del result

            # Load OSM data
            osm = pyrosm.OSM(temp_file.name)

            # Load filter configuration
            filter_config_file = (
                pathlib.Path(__file__).parent / "resources" / "poi_filter_config.yaml"
            )
            with open(filter_config_file, "r") as f:
                filter_config = yaml.safe_load(f)
            custom_filter = self.__create_custom_filter(filter_config)

            with warnings.catch_warnings():
                warnings.simplefilter(
                    action="ignore", category=pandas.errors.PerformanceWarning
                )
                pois = osm.get_pois(custom_filter=custom_filter)

            pois = self.__filter_pois(pois, filter_config)

            del osm

        index = {}
        for i in range(13, 24):
            index[i] = {"coords": [], "data": []}

        for poi_group, filter_info, filter in pois:

            # Process each poi_group as needed
            print(
                f"Processing {len(poi_group)} POIs for symbol {filter_info['symbol']} and filter {filter}"
            )
            for poi in poi_group.itertuples():
                if poi.id is None:
                    continue
                if poi.name is None:
                    continue

                lat = poi.lat
                lon = poi.lon
                poi_id = poi.id
                name = poi.name

                description = filter_info.get("description", "")
                symbol = filter_info.get("symbol", "unknown")

                if poi.geometry is not None and poi.geometry.geom_type != "Point":
                    local_geometry = LocalProjection(poi.geometry).to_local(
                        poi.geometry
                    )
                    radius = shapely.minimum_bounding_radius(local_geometry)
                    print(
                        f"Calculated radius for POI {poi_id} ({name}): {radius} meters"
                    )
                else:
                    radius = None

                rank = calculate_rank(radius=radius, place=poi.place)

                index[rank]["coords"].append((lat, lon))
                index[rank]["data"].append((poi_id, name, description, symbol, filter))

        return index
