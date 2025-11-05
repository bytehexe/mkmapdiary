import dataclasses
import pathlib

import whenever


@dataclasses.dataclass(kw_only=True)
class AssetRecord:
    """Model for storing asset data in the database."""

    id: int | None = None
    path: pathlib.Path
    type: str
    timestamp_utc: whenever.Instant | None = None
    timestamp_geo: whenever.ZonedDateTime | None = None
    display_date: whenever.Date | None = None
    latitude: float | None = None
    longitude: float | None = None
    approx: bool | None = None
    orientation: int | None = None
