import json
import logging
import tempfile

from PIL import Image
from pydantic import TypeAdapter

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

            adapter = TypeAdapter(AssetMetadata)
            schema = adapter.json_schema()
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
                        {},
                        message_params={"images": [tmpfile.name]},
                        format=schema,
                    )

                try:
                    metadata_dict = json.loads(result)
                    metadata = adapter.validate_python(metadata_dict)
                except Exception as e:
                    logger.debug(f"Failed to parse AI response, retrying... ({e})")
                    continue
                else:
                    asset.metadata = metadata
                    break

            logger.debug(f"Updated metadata for {asset.path}: {asset.metadata}")
