import dataclasses
import pathlib

import imagehash
import whenever


@dataclasses.dataclass
class AssetMetadata:
    XML_ROOT_TAG = "metadata"
    identifier: str | None = dataclasses.field(
        default=None,
        metadata={"xml": {"name": "dc:identifier", "show_placeholder": False}},
    )
    title: str | None = dataclasses.field(
        default=None, metadata={"xml": {"name": "dc:title"}}
    )
    description: str | None = dataclasses.field(
        default=None, metadata={"xml": {"name": "dc:description"}}
    )  # or dc:abstract
    subject: list[str] = dataclasses.field(
        default_factory=list, metadata={"xml": {"name": "dc:subject"}}
    )
    coverage: list[str] = dataclasses.field(
        default_factory=list,
        metadata={"xml": {"name": "dc:coverage", "show_placeholder": False}},
    )
    created: str | None = dataclasses.field(
        default=None,
        metadata={"xml": {"name": "dc:created", "show_placeholder": False}},
    )
    media_type: str | None = dataclasses.field(
        default=None, metadata={"xml": {"name": "dc:type", "show_placeholder": False}}
    )


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
    duplicate: bool = False
    quality: float | None = None
    metadata: AssetMetadata | None = None
    image_hash: imagehash.ImageHash | None = None
