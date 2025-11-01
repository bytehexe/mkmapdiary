import json
from typing import Any, List, NamedTuple


def get_hash(map_data: Any) -> str:
    import hashlib

    map_data_str = json.dumps(map_data, sort_keys=True)
    return hashlib.sha256(map_data_str.encode("utf-8")).hexdigest()


class Poi(NamedTuple):
    coords: List[float]
    osm_id: str
    name: str
    description: str
    symbol: str
    filter: str
    rank: int
