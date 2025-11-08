import dataclasses
import pathlib
import threading
from typing import Any

import whenever

from mkmapdiary.lib.asset import AssetRecord


class AssetRegistry:
    def __init__(self) -> None:
        # Note: Asset list is append/update only; no delete!
        self.__assets: list[AssetRecord] = []
        self.lock = threading.RLock()

        self.has_display_date = False

    @property
    def next_id(self) -> int:
        with self.lock:
            return len(self.__assets) + 1

    @property
    def assets(self) -> list[AssetRecord]:
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

    def update_asset(self, asset_record: AssetRecord | dict[str, Any]) -> None:
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

    def get_asset_by_id(self, asset_id: int) -> AssetRecord | None:
        """Get an asset by its ID."""
        with self.lock:
            for asset in self.__assets:
                if asset.id == asset_id:
                    return asset
            return None

    def get_asset_by_path(self, path: str | pathlib.Path) -> AssetRecord | None:
        """Get an asset by its path."""
        path_str = str(path)
        with self.lock:
            for asset in self.__assets:
                if str(asset.path) == path_str:
                    return asset
            return None

    def get_all_assets(self) -> list[AssetRecord]:
        with self.lock:
            # Sort by utc, handling None values
            sorted_assets = sorted(
                self.__assets, key=lambda x: x.timestamp_utc or whenever.Instant.MIN
            )
            return sorted_assets

    def get_all_dates(self) -> list[whenever.Date]:
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
        self, asset_type: str | list[str] | tuple[str, ...]
    ) -> list[AssetRecord]:
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
            return sorted_assets

    def get_assets_by_date(
        self,
        date: whenever.Date | str,
        asset_type: str | list[str] | tuple[str, ...],
    ) -> list[AssetRecord]:
        if not self.has_display_date:
            raise ValueError(
                "AssetRegistry must track display dates to get assets by date"
            )

        # Convert string date to whenever.Date if needed
        if isinstance(date, str):
            date = whenever.Date.parse_iso(date)

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
            return sorted_assets

    def get_geotagged_asset_by_path(
        self, path: str | pathlib.Path
    ) -> AssetRecord | None:
        path_str = str(path)
        with self.lock:
            for asset in self.__assets:
                if (
                    str(asset.path) == path_str
                    and asset.latitude is not None
                    and asset.longitude is not None
                ):
                    return asset
            return None

    def get_geotagged_assets(
        self, asset_type: str | list[str] | tuple[str, ...] | None = None
    ) -> list[AssetRecord]:
        """Get all geotagged assets, optionally filtered by asset type(s)."""
        if asset_type is not None:
            if isinstance(asset_type, str):
                asset_types = {asset_type}
            else:
                asset_types = set(asset_type)
        else:
            asset_types = None

        with self.lock:
            filtered_assets = []
            for asset in self.__assets:
                if (
                    asset.latitude is not None
                    and asset.longitude is not None
                    and (asset_types is None or asset.type in asset_types)
                ):
                    filtered_assets.append(asset)

            # Sort by utc timestamp
            sorted_assets = sorted(
                filtered_assets, key=lambda x: x.timestamp_utc or whenever.Instant.MIN
            )
            return sorted_assets

    def __mkrow(self, headers: list[str], asset: AssetRecord) -> list[Any]:
        row = list(dataclasses.astuple(asset))

        for i, (header, value) in enumerate(zip(headers, row, strict=False)):
            if header == "embedding" and value is not None:
                value = "[...]"
            row[i] = value

        return row

    def dump(self, asset_type: str | None = None) -> tuple[list[Any], list[str]]:
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
                rows.append(self.__mkrow(headers, asset))

            return rows, headers

    def get_unpositioned_assets(self) -> list[AssetRecord]:
        with self.lock:
            result = []
            for asset in self.__assets:
                if (
                    asset.latitude is None or asset.longitude is None
                ) and asset.type != "gpx":
                    result.append(asset)
            # Sort by utc timestamp
            sorted_assets = sorted(
                result, key=lambda x: x.timestamp_utc or whenever.Instant.MIN
            )
            return sorted_assets

    def update_asset_position(
        self, asset_id: int, latitude: float, longitude: float, approx: bool
    ) -> None:
        self.update_asset(
            {
                "id": asset_id,
                "latitude": latitude,
                "longitude": longitude,
                "approx": approx,
            }
        )

    def get_geotagged_journal_dates(self) -> list[whenever.Date]:
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
