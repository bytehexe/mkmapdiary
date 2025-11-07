from dataclasses import dataclass, field


@dataclass
class AssetSelection:
    identifier: list[str] = field(metadata={"xml": {"name": "dc:identifier"}})


@dataclass
class ImageQuality:
    isokay: bool


@dataclass
class QualityAspects:
    lighting: float
    composition: float
    focus_and_sharpness: float
    color_balance: float
    contrast_and_depth: float
    subject_expression: float
    storytelling: float
