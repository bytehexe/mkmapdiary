from abc import abstractmethod

from mkmapdiary.lib.asset import AssetRecord
from mkmapdiary.postprocessors.base.basePostprocessor import BasePostprocessor


class SingleAssetPostprocessor(BasePostprocessor):
    """Base class for postprocessors that handle a single asset type."""

    @classmethod
    def filter(cls, asset: AssetRecord) -> bool:
        raise NotImplementedError("Subclasses must implement the filter method.")

    @abstractmethod
    def processSingleAsset(self, asset: AssetRecord) -> None:
        raise NotImplementedError("Subclasses must implement the processAsset method.")
