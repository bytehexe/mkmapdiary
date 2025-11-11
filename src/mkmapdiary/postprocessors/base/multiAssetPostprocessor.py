from abc import abstractmethod

from mkmapdiary.lib.asset import AssetRecord
from mkmapdiary.postprocessors.base.basePostprocessor import BasePostprocessor


class MultiAssetPostprocessor(BasePostprocessor):
    """Base class for postprocessors that handle multiple asset types."""

    @abstractmethod
    def processAllAssets(self, assets: list[AssetRecord]) -> None:
        raise NotImplementedError(
            "Subclasses must implement the processAllAssets method."
        )
