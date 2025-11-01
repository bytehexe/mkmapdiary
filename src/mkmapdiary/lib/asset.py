import dataclasses
import datetime as datetime_
import pathlib
from typing import Optional


@dataclasses.dataclass(kw_only=True)
class AssetRecord:
    """Model for storing asset data in the database."""

    id: Optional[int] = None
    path: pathlib.Path
    type: str
    datetime: Optional[datetime_.datetime] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    approx: Optional[bool] = None
    orientation: Optional[int] = None


@dataclasses.dataclass(kw_only=True)
class AssetMetadata:
    """Subset of AssetRecord for storing metadata key-value pairs."""

    datetime: Optional[datetime_.datetime] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    orientation: Optional[int] = None


def update_asset_metadata(
    asset: AssetRecord,
    asset_meta: AssetMetadata,
) -> AssetRecord:
    return dataclasses.replace(asset, **dataclasses.asdict(asset_meta))
