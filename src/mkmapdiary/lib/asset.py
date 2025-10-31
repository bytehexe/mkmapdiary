import datetime
from pathlib import PosixPath
from typing import NamedTuple, Optional, Union


class AssetMeta:
    def __init__(
        self,
        timestamp: Optional[datetime.datetime] = None,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
    ):
        self.timestamp = timestamp
        self.latitude = latitude
        self.longitude = longitude

    timestamp: Optional[datetime.datetime]
    latitude: Optional[float]
    longitude: Optional[float]

    __slots__ = ["timestamp", "latitude", "longitude"]

    def _asdict(self) -> dict:
        return {
            "timestamp": self.timestamp,
            "latitude": self.latitude,
            "longitude": self.longitude,
        }

    def update(self, other: Union[dict, "AssetMeta"]):
        if isinstance(other, AssetMeta):
            other = other._asdict()

        for key, value in other.items():
            if value is not None:
                setattr(self, key, value)


class Asset(NamedTuple):
    path: PosixPath
    type: str
    meta: AssetMeta
