import logging

import ollama

from mkmapdiary.lib.asset import AssetRecord
from mkmapdiary.postprocessors.base.multiAssetPostprocessor import (
    MultiAssetPostprocessor,
)

logger = logging.getLogger(__name__)


class ImageEmbedder(MultiAssetPostprocessor):
    """Postprocessor that computes and stores image embeddings for duplicate detection."""

    @property
    def info(self) -> str:
        return "Embedding images for semantic analysis."

    def processAllAssets(self, assets: list[AssetRecord]) -> None:
        for asset in assets:
            if asset.type != "image":
                continue

            if asset.metadata is None:
                continue

            # Compute embedding using Ollama
            try:
                text = asset.metadata.description
                if text is None:
                    continue

                response = ollama.embed(model="nomic-embed-text:latest", input=text)
                asset.embedding = response["embeddings"][0]
            except Exception as e:
                logger.warning(
                    f"Failed to compute embedding for asset {asset.path}: {e}"
                )
                asset.embedding = None
