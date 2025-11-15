import dataclasses

import numpy as np
import whenever
from sklearn.metrics.pairwise import haversine_distances


@dataclasses.dataclass
class StatisticEntry:
    time_moving: float = 0.0
    distance: float = 0.0
    elevation_gain: float = 0.0
    elevation_loss: float = 0.0


class Statistics:
    THRESHOLDS = {
        # Upper speed thresholds in m/s
        "movement": 0.2,
        "unrealistic": 250.0,  # Ignore unrealistic speeds (previously "air" threshold)
    }

    def __init__(self) -> None:
        self.entries: dict[str, StatisticEntry] = {
            "total": StatisticEntry(),
        }
        self.__time: whenever.Instant | None = None
        self.__position: tuple[float, float] | None = None
        self.__elevation: float | None = None

    def reset(self) -> None:
        self.__time = None
        self.__position = None
        self.__elevation = None

    def __set_point(
        self,
        time: whenever.Instant,
        position: tuple[float, float],  # (lon, lat)
        elevation: float | None = None,
    ) -> None:
        self.__time = time
        self.__position = position
        self.__elevation = elevation

    def __set_elevation(
        self,
        mode: str,
        elevation: float | None = None,
    ) -> None:
        if elevation is None or self.__elevation is None:
            return

        delta = elevation - self.__elevation
        if delta > 0:
            self.entries[mode].elevation_gain += delta
        else:
            self.entries[mode].elevation_loss += -delta

    def add_entry(
        self,
        time: whenever.Instant,
        position: tuple[float, float],  # (lon, lat)
        elevation: float | None = None,
    ) -> None:
        if self.__time is None:
            self.__set_point(time, position, elevation)
            return

        assert self.__time is not None
        assert self.__position is not None

        time_delta = (time - self.__time).in_seconds()
        # calculate distance using haversine
        distance = 0.0
        # Convert from interface format (lon, lat) to haversine format (lat, lon)
        pos1 = np.radians(np.array([[self.__position[1], self.__position[0]]]))
        pos2 = np.radians(np.array([[position[1], position[0]]]))
        distance = (
            haversine_distances(pos1, pos2)[0][0] * 6371000
        )  # radius of Earth in meters

        speed = distance / time_delta if time_delta > 0 else 0.0

        if speed > self.THRESHOLDS["unrealistic"]:
            # Ignore unrealistic speeds
            self.reset()
            return

        self.entries["total"].distance += distance
        self.__set_elevation("total", elevation)

        if speed >= self.THRESHOLDS["movement"]:
            self.entries["total"].time_moving += time_delta

        self.__set_point(time, position, elevation)
