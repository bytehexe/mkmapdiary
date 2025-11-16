from collections.abc import Callable

import numpy as np
from imagehash import ImageHash, colorhash, whash
from PIL import Image

from mkmapdiary.lib.asset import AssetRecord
from mkmapdiary.postprocessors.base.singleAssetPostprocessor import (
    SingleAssetPostprocessor,
)


class ImageHasher(SingleAssetPostprocessor):
    """Postprocessor that computes and stores image hashes for duplicate detection."""

    @classmethod
    def filter(cls, asset: AssetRecord) -> bool:
        return asset.type == "image"

    def __init__(self, ai: Callable, config: dict) -> None:
        super().__init__(ai, config)
        self.__enabled = config["features"]["image_comparison"]["enabled"]

    @property
    def info(self) -> str:
        return "Hashing images for duplicate detection."

    def processSingleAsset(self, asset: AssetRecord) -> None:
        if not self.__enabled:
            asset.image_hash = ImageHash(np.asarray([0]))
            asset.color_hash = ImageHash(np.asarray([0]))
            return

        with Image.open(asset.path) as img:
            asset.image_hash = whash(img)
            asset.color_hash = colorhash(img)
