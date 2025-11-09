import logging
from typing import Any

from mkmapdiary.lib.asset import AssetRecord
from mkmapdiary.postprocessors.base.multiAssetPostprocessor import (
    MultiAssetPostprocessor,
)

logger = logging.getLogger(__name__)


class ImageQualityAssessment(MultiAssetPostprocessor):
    @property
    def info(self) -> str:
        return "Assessing image quality."

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)

        # for now, we only have simple assessment
        from mkmapdiary.postprocessors.simpleImageQualityAssessment import (
            SimpleImageQualityAssessment,
        )

        self.assessor = SimpleImageQualityAssessment(self.ai, self.config)

    def processAllAssets(self, assets: list[AssetRecord]) -> None:
        self.assessor.processAllAssets(assets)

        # Log summary
        def get_quality(asset: AssetRecord) -> float:
            return asset.quality if asset.quality is not None else -1.0

        best_image = max(
            (asset for asset in assets if asset.type == "image"),
            key=get_quality,
            default=None,
        )
        worst_image = min(
            (asset for asset in assets if asset.type == "image"),
            key=get_quality,
            default=None,
        )
        if best_image:
            logger.debug(
                f"Best image: {best_image.path} (quality={best_image.quality:.3f})"
            )
        if worst_image:
            logger.debug(
                f"Worst image: {worst_image.path} (quality={worst_image.quality:.3f})"
            )
