from imagehash import colorhash, whash
from PIL import Image

from mkmapdiary.lib.asset import AssetRecord
from mkmapdiary.postprocessors.base.singleAssetPostprocessor import (
    SingleAssetPostprocessor,
)


class ImageHasher(SingleAssetPostprocessor):
    """Postprocessor that computes and stores image hashes for duplicate detection."""

    @property
    def info(self) -> str:
        return "Hashing images for duplicate detection."

    def processSingleAsset(self, asset: AssetRecord) -> None:
        if asset.type != "image":
            return

        with Image.open(asset.path) as img:
            asset.image_hash = whash(img)
            asset.color_hash = colorhash(img)
