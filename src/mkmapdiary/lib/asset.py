import dataclasses
import pathlib
from typing import Literal

import imagehash
import whenever
from pydantic import Field
from pydantic.dataclasses import dataclass as pydantic_dataclass


@pydantic_dataclass
class AssetMetadata:
    context: Literal["http://purl.org/dc/elements/1.1/"] = Field(
        alias="@context",
        default="http://purl.org/dc/elements/1.1/",
    )
    identifier: str | None = dataclasses.field(default=None)
    title: str | None = dataclasses.field(default=None)
    description: str | None = dataclasses.field(default=None)
    subject: list[str] = dataclasses.field(default_factory=list)
    coverage: list[str] = dataclasses.field(default_factory=list)
    created: str | None = dataclasses.field(default=None)
    media_type: str | None = dataclasses.field(default=None)


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
    is_duplicate: bool | None = None
    is_bad: bool = False
    quality: float | None = None
    entropy: float | None = None
    metadata: AssetMetadata | None = None
    image_hash: imagehash.ImageHash | None = None
    color_hash: imagehash.ImageHash | None = None
    embedding: list[float] | None = None
    effects: list[str] = dataclasses.field(default_factory=list)
