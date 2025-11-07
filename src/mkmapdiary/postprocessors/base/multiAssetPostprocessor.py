from mkmapdiary.lib.asset import AssetRecord
from mkmapdiary.postprocessors.base.basePostprocessor import BasePostprocessor


class MultiAssetPostprocessor(BasePostprocessor):
    """Base class for postprocessors that handle multiple asset types."""

    @property
    def info(self) -> str:
        return "Base multi-asset postprocessor."

    def processAllAssets(self, assets: list[AssetRecord]) -> None:
        raise NotImplementedError(
            "Subclasses must implement the processAllAssets method."
        )
