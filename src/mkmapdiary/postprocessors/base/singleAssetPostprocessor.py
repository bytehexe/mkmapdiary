from mkmapdiary.lib.asset import AssetRecord
from mkmapdiary.postprocessors.base.basePostprocessor import BasePostprocessor


class SingleAssetPostprocessor(BasePostprocessor):
    """Base class for postprocessors that handle a single asset type."""

    @property
    def info(self) -> str:
        return "Base single-asset postprocessor."

    def processSingleAsset(self, asset: AssetRecord) -> None:
        raise NotImplementedError("Subclasses must implement the processAsset method.")
