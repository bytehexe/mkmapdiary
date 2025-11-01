import datetime
import threading
from typing import Any, Dict, List, Optional, Tuple, Union

from mkmapdiary.lib.asset import AssetRecord


class AssetRegistry:
    def __init__(self) -> None:
        # Note: Asset list is append/update only; no delete!
        self._assets: List[AssetRecord] = []
        self.lock = threading.RLock()

    @property
    def next_id(self) -> int:
        with self.lock:
            return len(self._assets) + 1

    @property
    def assets(self) -> List[AssetRecord]:
        with self.lock:
            return self._assets.copy()

    def add_asset(self, asset_record: AssetRecord) -> None:
        with self.lock:
            assert asset_record.id is None, (
                "AssetRecord id must be None when adding a new asset"
            )
            asset_record.id = self.next_id

            self._assets.append(asset_record)

    def count_assets(self) -> int:
        with self.lock:
            return len(self._assets)

    def count_assets_by_date(self) -> dict[str, int]:
        with self.lock:
            date_counts: Dict[str, int] = {}
            for asset in self._assets:
                if asset.datetime:
                    date_str = asset.datetime.date().isoformat()
                    date_counts[date_str] = date_counts.get(date_str, 0) + 1
            return dict(sorted(date_counts.items()))

    def get_all_assets(self) -> List[str]:
        with self.lock:
            # Sort by datetime, handling None values
            sorted_assets = sorted(
                self._assets, key=lambda x: x.datetime or datetime.datetime.min
            )
            return [str(asset.path) for asset in sorted_assets]

    def get_all_dates(self) -> List[str]:
        with self.lock:
            dates = set()
            for asset in self._assets:
                if asset.datetime:
                    dates.add(asset.datetime.date().isoformat())
            return sorted(list(dates))

    def get_assets_by_type(
        self, asset_type: Union[str, List[str], Tuple[str, ...]]
    ) -> List[Tuple[str, str]]:
        if isinstance(asset_type, str):
            asset_types = {asset_type}
        else:
            asset_types = set(asset_type)

        with self.lock:
            filtered_assets = [
                asset for asset in self._assets if asset.type in asset_types
            ]
            # Sort by datetime
            sorted_assets = sorted(
                filtered_assets, key=lambda x: x.datetime or datetime.datetime.min
            )
            return [(str(asset.path), asset.type) for asset in sorted_assets]

    def get_assets_by_date(
        self, date: str, asset_type: Union[str, List[str], Tuple[str, ...]]
    ) -> List[Tuple[str, str]]:
        if isinstance(asset_type, str):
            asset_types = {asset_type}
        else:
            asset_types = set(asset_type)

        with self.lock:
            filtered_assets = []
            for asset in self._assets:
                if (
                    asset.datetime
                    and asset.datetime.date().isoformat() == date
                    and asset.type in asset_types
                ):
                    filtered_assets.append(asset)

            # Sort by datetime
            sorted_assets = sorted(
                filtered_assets, key=lambda x: x.datetime or datetime.datetime.min
            )
            return [(str(asset.path), asset.type) for asset in sorted_assets]

    def get_geo_by_name(self, name: str) -> Optional[dict[str, Union[str, float]]]:
        with self.lock:
            for asset in self._assets:
                if (
                    asset.path == name
                    and asset.latitude is not None
                    and asset.longitude is not None
                ):
                    return {
                        "name": str(asset.path),
                        "latitude": asset.latitude,
                        "longitude": asset.longitude,
                    }
            return None

    def dump(self, asset_type: Optional[str] = None) -> Tuple[List[Any], List[str]]:
        headers = ["ID", "Path", "Type", "DateTime", "Latitude", "Longitude", "approx"]
        with self.lock:
            if asset_type:
                filtered_assets = [
                    asset for asset in self._assets if asset.type == asset_type
                ]
            else:
                filtered_assets = self._assets

            rows = []
            for asset in filtered_assets:
                rows.append(
                    [
                        asset.id,
                        asset.path,
                        asset.type,
                        asset.datetime,
                        asset.latitude,
                        asset.longitude,
                        asset.approx,
                    ]
                )

            return rows, headers

    def get_unpositioned_assets(self) -> List[Tuple[int, Optional[str]]]:
        with self.lock:
            result = []
            for asset in self._assets:
                if (
                    asset.latitude is None or asset.longitude is None
                ) and asset.type != "gpx":
                    datetime_str = (
                        asset.datetime.isoformat() if asset.datetime else None
                    )
                    assert asset.id is not None
                    result.append((asset.id, datetime_str))
            return result

    def get_unpositioned_asset_paths(self) -> List[str]:
        with self.lock:
            result = []
            for asset in self._assets:
                if (
                    asset.latitude is None or asset.longitude is None
                ) and asset.type != "gpx":
                    result.append(str(asset.path))
            return result

    def update_asset_position(
        self, asset_id: int, latitude: float, longitude: float, approx: bool
    ) -> None:
        with self.lock:
            for asset in self._assets:
                if asset.id == asset_id:
                    asset.latitude = latitude
                    asset.longitude = longitude
                    asset.approx = approx
                    break

    def get_geotagged_journals(self) -> List[str]:
        with self.lock:
            dates = set()
            for asset in self._assets:
                if (
                    asset.latitude is not None
                    and asset.longitude is not None
                    and asset.type in ("markdown", "audio")
                    and asset.datetime
                ):
                    dates.add(asset.datetime.date().isoformat())
            return sorted(list(dates))

    def get_metadata(
        self, asset_path: str
    ) -> Optional[dict[str, Union[int, str, float, None]]]:
        with self.lock:
            for asset in self._assets:
                if asset.path == asset_path:
                    return {
                        "id": asset.id,
                        "timestamp": asset.datetime.isoformat()
                        if asset.datetime
                        else None,
                        "latitude": asset.latitude,
                        "longitude": asset.longitude,
                    }
            return None
