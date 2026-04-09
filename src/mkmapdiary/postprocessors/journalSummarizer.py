import json
import logging

from pydantic import TypeAdapter

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

            adapter = TypeAdapter(AssetMetadata)
            schema = adapter.json_schema()
            for _ in range(3):  # Retry up to 3 times
                result = self.ai(
                    "summarize_journal_entry",
                    {"text": content},
                    response_format=schema,
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
