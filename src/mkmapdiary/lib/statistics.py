import logging

import numpy as np
import whenever
from sklearn.metrics.pairwise import haversine_distances

logger = logging.getLogger(__name__)


class Statistics:
    THRESHOLDS = {
        "movement": 0.2,
        "unrealistic": 250.0,  # Ignore unrealistic speeds (previously "air" threshold)
    }

    def __init__(self) -> None:
        # Direct attributes instead of entries dictionary
        self.time_moving: float = 0.0
        self.total_time: float = 0.0
        self.distance: float = 0.0
        self.elevation_gain: float = 0.0
        self.elevation_loss: float = 0.0

        self.__time: whenever.Instant | None = None
        self.__first_time: whenever.Instant | None = None
        self.__position: tuple[float, float] | None = None
        self.__elevation: float | None = None

    def reset(self) -> None:
        self.__time = None
        self.__first_time = None
        self.__position = None
        self.__elevation = None

    def __set_point(
        self,
        time: whenever.Instant,
        position: tuple[float, float],  # (lon, lat)
    ) -> None:
        self.__time = time
        if self.__first_time is None:
            self.__first_time = time
        self.__position = position

    def __set_elevation(
        self,
        elevation: float | None,
        time_delta: float,
    ) -> None:
        if elevation is None:
            self.__elevation = None
            return
        elif self.__elevation is None:
            self.__elevation = elevation
            return

        delta = elevation - self.__elevation
        if time_delta > 0:
            elevation_rate = delta / time_delta
            if elevation_rate > 8 or elevation_rate < -8:
                # Ignore unrealistic elevation changes
                self.__elevation = elevation
                return

        if abs(delta) < 5:
            # Smooth out small elevation changes
            return

        if delta > 0:
            self.elevation_gain += delta
        else:
            self.elevation_loss += -delta
        self.__elevation = elevation

    def add_entry(
        self,
        time: whenever.Instant,
        position: tuple[float, float],  # (lon, lat)
        elevation: float | None = None,
    ) -> None:
        if self.__time is None:
            self.__set_point(time, position)
            self.__set_elevation(elevation, 0.0)
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

        self.distance += distance
        self.__set_elevation(elevation, time_delta)

        if speed >= self.THRESHOLDS["movement"]:
            self.time_moving += time_delta

        # Update total time (time between first and last timestamp)
        if self.__first_time is not None:
            self.total_time = (time - self.__first_time).in_seconds()

        self.__set_point(time, position)
