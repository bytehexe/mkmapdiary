import logging

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

            asset.metadata = self.ai(
                "summarize_journal_entry",
                {"text": content},
                schema=AssetMetadata,
            )

            logger.debug(f"Updated metadata for {asset.path}: {asset.metadata}")
