import json
from collections import namedtuple


def get_hash(map_data: dict) -> str:
    import hashlib

    map_data_str = json.dumps(map_data, sort_keys=True)
    return hashlib.sha256(map_data_str.encode("utf-8")).hexdigest()


Poi = namedtuple(
    "Poi", ["coords", "osm_id", "name", "description", "symbol", "filter", "rank"]
)
