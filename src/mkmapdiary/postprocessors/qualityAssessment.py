import logging
import tempfile
from dataclasses import asdict

import llm_dataclass
import numpy as np
from PIL import Image

from mkmapdiary.lib.asset import AssetRecord
from mkmapdiary.lib.llm_classes import QualityAspects
from mkmapdiary.postprocessors.base.multiAssetPostprocessor import (
    MultiAssetPostprocessor,
)

logger = logging.getLogger(__name__)


class QualityAssessment(MultiAssetPostprocessor):
    @property
    def info(self) -> str:
        return "Assessing image quality using AI."

    def processAllAssets(self, assets: list[AssetRecord]) -> None:
        for asset in assets:
            if asset.type not in ("image"):
                continue

            self.config["site"]["locale"].split("_")[0]
            schema = llm_dataclass.Schema(QualityAspects, root="rating")
            for _ in range(3):  # Retry up to 3 times
                with tempfile.NamedTemporaryFile(
                    delete=False, suffix=".jpg"
                ) as tmpfile:
                    # Resize image if too large
                    with Image.open(asset.path) as img:
                        max_size = 1024
                        if max(img.size) > max_size:
                            img.thumbnail((max_size, max_size))
                        img.save(tmpfile.name, format="JPEG")

                    result = self.ai(
                        "assess_image_quality",
                        {"example": schema.dumps()},
                        message_params={"images": [tmpfile.name]},
                    )

                try:
                    quality_aspects = schema.loads(result)
                except Exception as e:
                    logger.debug(f"Failed to parse AI response, retrying... ({e})")
                    continue
                else:
                    quality = np.mean(np.array(list(asdict(quality_aspects).values())))
                    asset.quality = float(quality)
                    break

            logger.debug(f"Updated asset quality for {asset.path}: {asset.quality}")
