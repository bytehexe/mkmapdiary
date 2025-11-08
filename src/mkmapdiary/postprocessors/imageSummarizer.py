import logging
import tempfile

import llm_dataclass
from PIL import Image

from mkmapdiary.lib.asset import AssetMetadata, AssetRecord
from mkmapdiary.postprocessors.base.multiAssetPostprocessor import (
    MultiAssetPostprocessor,
)

logger = logging.getLogger(__name__)


class ImageSummarizer(MultiAssetPostprocessor):
    @property
    def info(self) -> str:
        return "Summarizing images using AI."

    def processAllAssets(self, assets: list[AssetRecord]) -> None:
        return  # --- IGNORE ---
        for asset in assets:
            if asset.type not in ("image"):
                continue

            lang = self.config["site"]["locale"].split("_")[0]
            schema = llm_dataclass.Schema(
                AssetMetadata, root_attributes={"xml:lang": lang}
            )
            for _ in range(3):  # Retry up to 3 times
                with tempfile.NamedTemporaryFile(
                    delete=False, suffix=".jpg"
                ) as tmpfile:
                    # Resize image if too large
                    with Image.open(asset.path) as img:
                        max_size = 512
                        if max(img.size) > max_size:
                            img.thumbnail((max_size, max_size))
                        img.save(tmpfile.name, format="JPEG")

                    result = self.ai(
                        "summarize_image",
                        {"example": schema.dumps()},
                        message_params={"images": [tmpfile.name]},
                    )

                try:
                    metadata = schema.loads(result)
                except Exception as e:
                    logger.debug(f"Failed to parse AI response, retrying... ({e})")
                    continue
                else:
                    asset.metadata = metadata
                    break

            logger.debug(f"Updated metadata for {asset.path}: {asset.metadata}")
