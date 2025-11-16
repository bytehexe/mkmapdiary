import logging
from typing import Any

from mkmapdiary.lib.asset import AssetRecord
from mkmapdiary.postprocessors.base.multiAssetPostprocessor import (
    MultiAssetPostprocessor,
)

logger = logging.getLogger(__name__)


class ConstImageQualityAssessment(MultiAssetPostprocessor):
    @property
    def info(self) -> str:
        return "Assessing image quality using a constant value."

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)

    def processAllAssets(self, assets: list[AssetRecord]) -> None:
        for asset in assets:
            if asset.type == "image":
                asset.quality = 0.5  # Assign a constant medium quality score
