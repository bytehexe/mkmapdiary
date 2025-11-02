import dataclasses
import pathlib
import threading
from typing import Any, Dict, List, Optional, Tuple, Union

import whenever

from mkmapdiary.lib.asset import AssetRecord


class AssetRegistry:
    def __init__(self) -> None:
        # Note: Asset list is append/update only; no delete!
        self.__assets: List[AssetRecord] = []
        self.lock = threading.RLock()

        self.has_display_date = False

    @property
    def next_id(self) -> int:
        with self.lock:
            return len(self.__assets) + 1

    @property
    def assets(self) -> List[AssetRecord]:
        """Get a copy of the list of all asset records.
        Modifications to the returned list will not affect the registry.
        Modifications to the asset records themselves will affect the registry."""
        with self.lock:
            return self.__assets.copy()

    def add_asset(self, asset_record: AssetRecord) -> None:
        """Add a new asset record to the registry."""
        with self.lock:
            assert asset_record.id is None, (
                "AssetRecord id must be None when adding a new asset"
            )
            asset_record.id = self.next_id

            self.__assets.append(asset_record)

    def update_asset(self, asset_record: Union[AssetRecord, Dict[str, Any]]) -> None:
        """Update an existing asset record.
        If a record is provided, only non-None fields in asset_record will be updated."""
        if isinstance(asset_record, dict):
            asset_dict = asset_record
        else:
            asset_dict = dataclasses.asdict(asset_record)
            asset_dict = {k: v for k, v in asset_dict.items() if v is not None}

        with self.lock:
            assert asset_dict["id"] is not None, (
                "AssetRecord id must not be None when updating an asset"
            )
            for idx, existing_asset in enumerate(self.__assets):
                if existing_asset.id == asset_dict["id"]:
                    self.__assets[idx] = dataclasses.replace(
                        existing_asset, **asset_dict
                    )
                    return
            raise ValueError(f"Asset with id {asset_dict['id']} not found")

    def count_assets(self) -> int:
        """Get the total number of assets in the registry."""
        with self.lock:
            return len(self.__assets)

    def get_all_assets(self) -> List[str]:
        with self.lock:
            # Sort by utc, handling None values
            sorted_assets = sorted(
                self.__assets, key=lambda x: x.timestamp_utc or whenever.Instant.MIN
            )
            return [str(asset.path) for asset in sorted_assets]

    def get_all_dates(self) -> List[whenever.Date]:
        assert self.has_display_date, (
            "AssetRegistry must track display dates to get all dates"
        )

        with self.lock:
            dates = set()
            for asset in self.__assets:
                if asset.display_date:
                    dates.add(asset.display_date)
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
                asset for asset in self.__assets if asset.type in asset_types
            ]
            # Sort by utc timestamp
            sorted_assets = sorted(
                filtered_assets, key=lambda x: x.timestamp_utc or whenever.Instant.MIN
            )
            return [(str(asset.path), asset.type) for asset in sorted_assets]

    def get_assets_by_date(
        self,
        date: whenever.Date,
        asset_type: Union[str, List[str], Tuple[str, ...]],
    ) -> List[Tuple[pathlib.Path, str]]:
        if not self.has_display_date:
            raise ValueError(
                "AssetRegistry must track display dates to get assets by date"
            )

        if isinstance(asset_type, str):
            asset_types = {asset_type}
        else:
            asset_types = set(asset_type)

        with self.lock:
            filtered_assets = []
            for asset in self.__assets:
                if (
                    asset.display_date
                    and asset.display_date == date
                    and asset.type in asset_types
                ):
                    filtered_assets.append(asset)

            # Sort by utc timestamp
            sorted_assets = sorted(
                filtered_assets, key=lambda x: x.timestamp_utc or whenever.Instant.MIN
            )
            return [(asset.path, asset.type) for asset in sorted_assets]

    def get_geo_by_name(self, name: str) -> Optional[dict[str, Union[str, float]]]:
        with self.lock:
            for asset in self.__assets:
                if (
                    str(asset.path) == name
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
        # Get all fields of AssetRecord, in order of definition, get their names from __dataclass_fields__
        headers = [field.name for field in AssetRecord.__dataclass_fields__.values()]
        with self.lock:
            if asset_type:
                filtered_assets = [
                    asset for asset in self.__assets if asset.type == asset_type
                ]
            else:
                filtered_assets = self.__assets

            rows = []
            for asset in filtered_assets:
                rows.append(list(dataclasses.astuple(asset)))

            return rows, headers

    def get_unpositioned_assets(self) -> List[Tuple[int, Optional[whenever.Instant]]]:
        with self.lock:
            result = []
            for asset in self.__assets:
                if (
                    asset.latitude is None or asset.longitude is None
                ) and asset.type != "gpx":
                    timestamp_val = asset.timestamp_utc if asset.timestamp_utc else None
                    assert asset.id is not None
                    result.append((asset.id, timestamp_val))
            return result

    def get_unpositioned_asset_paths(self) -> List[str]:
        with self.lock:
            result = []
            for asset in self.__assets:
                if (
                    asset.latitude is None or asset.longitude is None
                ) and asset.type != "gpx":
                    result.append(str(asset.path))
            return result

    def update_asset_position(
        self, asset_id: int, latitude: float, longitude: float, approx: bool
    ) -> None:
        with self.lock:
            for asset in self.__assets:
                if asset.id == asset_id:
                    asset.latitude = latitude
                    asset.longitude = longitude
                    asset.approx = approx
                    break

    def get_geotagged_journals(self) -> List[whenever.Date]:
        with self.lock:
            dates = set()
            for asset in self.__assets:
                if (
                    asset.latitude is not None
                    and asset.longitude is not None
                    and asset.type in ("markdown", "audio")
                    and asset.display_date
                ):
                    dates.add(asset.display_date)
            return sorted(list(dates))

    def get_metadata(
        self, asset_path: str
    ) -> Optional[dict[str, Union[int, str, float, None]]]:
        with self.lock:
            for asset in self.__assets:
                if str(asset.path) == asset_path:
                    return {
                        "id": asset.id,
                        "timestamp": asset.timestamp_utc.format_iso()
                        if asset.timestamp_utc
                        else None,
                        "latitude": asset.latitude,
                        "longitude": asset.longitude,
                    }
            return None
