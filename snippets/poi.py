import warnings

import pandas.errors
import pyrosm
import yaml

fp = pyrosm.get_data("berlin")
print("Filepath to test data:", fp)

osm = pyrosm.OSM(fp)

print("Applying custom filter for POI extraction...")

with open("snippets/filter_config.yaml", "r") as f:
    filter_config = yaml.safe_load(f)

# Pre-filtering to reduce data size

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

print("Custom filter for POI extraction:", custom_filter)

with warnings.catch_warnings():
    warnings.simplefilter(action="ignore", category=pandas.errors.PerformanceWarning)
    pois = osm.get_pois(custom_filter=custom_filter)

print("Number of POIs found:", len(pois))

# for poi in pois.itertuples():
#     if poi.name is None:
#         continue
#     if poi.osm_type != "node":
#         continue

#     with open("snippets/test.yaml", "w") as f:
#         yaml.dump(poi._asdict(), f, indent=2)

#     print(f"- {poi._asdict().get('id', None)}: {poi._asdict().get('name', None)} ({poi._asdict().get('tourism', None)}, {poi._asdict().get('public_transport', None)}, {poi._asdict().get('place', None)}, {poi._asdict().get('leisure', None)})")
#     break

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

            count = pois[filter_expression].shape[0]
            print(f"{symbol} ({filter}):", count)
        except KeyError as e:
            print(f"{symbol} ({filter}): 0 (key not found: {e})")
            continue

        pois = pois[~filter_expression]


# 1. Load OSM data with custom_filter
# 2. Filter POIs further:
#    - Places of type city, town, village, etc.
#    - POIs
#    Apply filter, then reduce the dataset to the inverse of the filter
# 3. Save POIs to binary json
#
# Storage: [(lat, lon), ...], [(id, name, entry_id, kv_parameters), ...], entry=[(symbol, description), ...]
# Two separate indexes: one for places, one for POIs
