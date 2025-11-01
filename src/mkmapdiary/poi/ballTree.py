from typing import Any, Generator, List, Tuple

import numpy as np
from sklearn.neighbors import BallTree as SklearnBallTree

from mkmapdiary.poi.common import Poi


class BallTree:
    def __init__(
        self,
        sklearn_ball_tree: SklearnBallTree,
        pois: List[List[Any]],
        filter_config: List,
    ) -> None:
        self.__sklearn_ball_tree = sklearn_ball_tree
        self.__pois = pois
        self.__filter_config = filter_config

    def query_radius(self, X: np.ndarray, r: float) -> List[Poi]:
        # Interface expects (lat, lon) format, sklearn haversine expects (lat, lon)
        X = np.radians(X)  # X is (lat, lon), sklearn haversine expects (lat, lon)
        rh = r / 6371000.0  # Convert radius from meters to radians
        return list(self.__find(self.__sklearn_ball_tree.query_radius([X], rh)[0]))

    def query(self, X: np.ndarray, k: int = 1) -> Tuple[List[Poi], List[float]]:
        # Interface expects (lat, lon) format, sklearn haversine expects (lat, lon)
        X = np.radians(X)  # X is (lat, lon), sklearn haversine expects (lat, lon)
        result = self.__sklearn_ball_tree.query([X], k)
        return list(self.__find(result[1][0])), [x * 6371000.0 for x in result[0][0]]

    def __find(self, indices: np.ndarray) -> Generator[Poi, None, None]:
        for i in indices:
            yield self.__create_poi(i)

    def __create_poi(self, index: int) -> Poi:
        # Convert from sklearn storage format (lat, lon) to interface format (lon, lat)
        lat, lon = np.degrees(self.__sklearn_ball_tree.data[index])
        coord = [lon, lat]  # Interface uses (lon, lat) format
        poi_data = self.__pois[index]
        assert len(poi_data) == 4, "POI data structure has changed."
        assert len(poi_data[2]) == 2, "POI filter reference structure has changed."
        assert type(poi_data[2][0]) is int, (
            f"POI filter item ID should be an integer, but got {type(poi_data[2][0])}."
        )
        assert type(poi_data[2][1]) is int, (
            f"POI filter expression ID should be an integer, but got {type(poi_data[2][1])}."
        )
        filter_item = self.__filter_config[poi_data[2][0]]
        description = filter_item.get("description", "")
        symbol = filter_item.get("symbol", "unknown")
        filter_expression = filter_item["filters"][poi_data[2][1]]

        return Poi(
            coords=list(coord),
            osm_id=poi_data[0],
            name=poi_data[1],
            description=description,
            symbol=symbol,
            filter=filter_expression,
            rank=poi_data[3],
        )
