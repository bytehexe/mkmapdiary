from mkmapdiary.poi.common import Poi
import numpy as np


class BallTree:

    def __init__(self, sklearn_ball_tree, pois, filter_config):
        self.__sklearn_ball_tree = sklearn_ball_tree
        self.__pois = pois
        self.__filter_config = filter_config

    def query_radius(self, X, r):
        X = np.radians(X)  # X is (lat, lon), sklearn haversine expects (lat, lon)
        rh = r / 6371000.0  # Convert radius from meters to radians
        return self.__find(self.__sklearn_ball_tree.query_radius([X], rh)[0])

    def query(self, X, k=1):
        X = np.radians(X)  # X is (lat, lon), sklearn haversine expects (lat, lon)
        result = self.__sklearn_ball_tree.query([X], k)
        return list(self.__find(result[1][0])), [x * 6371000.0 for x in result[0][0]]

    def __find(self, indices):
        for i in indices:
            yield self.__create_poi(i)

    def __create_poi(self, index) -> Poi:
        coord = [
            float(x) for x in np.degrees(self.__sklearn_ball_tree.data[index])
        ]  # coords are stored as (lat, lon)
        poi_data = self.__pois[index]
        assert len(poi_data) == 4, "POI data structure has changed."
        assert len(poi_data[2]) == 2, "POI filter reference structure has changed."
        assert (
            type(poi_data[2][0]) == int
        ), f"POI filter item ID should be an integer, but got {type(poi_data[2][0])}."
        assert (
            type(poi_data[2][1]) == int
        ), f"POI filter expression ID should be an integer, but got {type(poi_data[2][1])}."
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
