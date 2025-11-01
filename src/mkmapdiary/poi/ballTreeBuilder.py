import logging

import numpy as np
from sklearn.neighbors import BallTree as SkBallTree

from mkmapdiary.poi.ballTree import BallTree

logger = logging.getLogger(__name__)


class BallTreeBuilder:
    def __init__(self, filter_config: dict):
        self.__coords: list[tuple[float, float]] = []
        self.__pois: list[list] = []
        self.__filter_config = filter_config

    def load(self, index_data: dict, min_rank: int, max_rank: int) -> None:
        for rank in range(min_rank, max_rank + 1):
            self.__coords.extend(index_data.get(rank, {}).get("coords", []))
            self.__pois.extend(index_data.get(rank, {}).get("data", []))
            assert len(self.__coords) == len(self.__pois), (
                "Mismatch between coordinates and POI data lengths"
            )

    def __build(self) -> SkBallTree:
        logger.info("Generating ball tree ...")
        ball_tree = SkBallTree(
            np.radians(
                self.__coords,
            ),  # coords are (lat, lon), sklearn haversine expects (lat, lon)
            leaf_size=40,
            metric="haversine",
        )
        return ball_tree

    def build(self) -> BallTree:
        data = self.__build()
        return BallTree(data, self.__pois, self.__filter_config)
