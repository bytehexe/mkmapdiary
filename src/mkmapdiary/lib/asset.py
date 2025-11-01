import dataclasses
import pathlib
from typing import Optional

import whenever


@dataclasses.dataclass(kw_only=True)
class AssetRecord:
    """Model for storing asset data in the database."""

    id: Optional[int] = None
    path: pathlib.Path
    type: str
    timestamp_utc: Optional[whenever.Instant] = None
    timestamp_geo: Optional[whenever.ZonedDateTime] = None
    display_date: Optional[whenever.Date] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    approx: Optional[bool] = None
    orientation: Optional[int] = None


@dataclasses.dataclass(kw_only=True)
class AssetMetadata:
    """Subset of AssetRecord for storing metadata key-value pairs."""

    timestamp_utc: Optional[whenever.Instant] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    orientation: Optional[int] = None


def update_asset_metadata(
    asset: AssetRecord,
    asset_meta: AssetMetadata,
) -> AssetRecord:
    return dataclasses.replace(asset, **dataclasses.asdict(asset_meta))
