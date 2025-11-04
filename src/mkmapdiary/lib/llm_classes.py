from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class Metadata:
    identifier: Optional[str] = field(
        metadata={"xml": {"name": "dc:identifier", "show_placeholder": False}}
    )
    title: str = field(metadata={"xml": {"name": "dc:title"}})
    description: str = field(
        metadata={"xml": {"name": "dc:description"}}
    )  # or dc:abstract
    subject: List[str] = field(metadata={"xml": {"name": "dc:subject"}})
    coverage: List[str] = field(
        metadata={"xml": {"name": "dc:coverage", "show_placeholder": False}}
    )
    created: Optional[str] = field(
        metadata={"xml": {"name": "dc:created", "show_placeholder": False}}
    )
    media_type: Optional[str] = field(
        metadata={"xml": {"name": "dc:type", "show_placeholder": False}}
    )


@dataclass
class AssetSelection:
    identifier: List[str] = field(metadata={"xml": {"name": "dc:identifier"}})


@dataclass
class ImageQuality:
    isokay: bool


@dataclass
class DuplicateEvaluation:
    lighting: str
    composition: str
    focus_and_sharpness: str
    color_balance: str
    contrast_and_depth: str
    subject_expression: str
    storytelling: str
