import logging

import llm_dataclass

from mkmapdiary.lib.asset import AssetMetadata, AssetRecord
from mkmapdiary.postprocessors.base.multiAssetPostprocessor import (
    MultiAssetPostprocessor,
)

logger = logging.getLogger(__name__)


class JournalSummarizer(MultiAssetPostprocessor):
    @property
    def info(self) -> str:
        return "Summarizing journal entries using AI."

    def processAllAssets(self, assets: list[AssetRecord]) -> None:
        for asset in assets:
            if asset.type not in ("markdown", "text", "audio"):
                continue

            path = asset.path
            # For audio, add the .md extension
            if asset.type == "audio":
                path = path.with_suffix(".mp3.md")

            with path.open("r", encoding="utf-8") as f:
                content = f.read()

            lang = self.config["site"]["locale"].split("_")[0]
            schema = llm_dataclass.Schema(
                AssetMetadata, root_attributes={"xml:lang": lang}
            )
            for _ in range(3):  # Retry up to 3 times
                result = self.ai(
                    "summarize_journal_entry",
                    {"text": content, "example": schema.dumps()},
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
