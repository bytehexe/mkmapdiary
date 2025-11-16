from collections.abc import Callable

import numpy as np
from PIL import Image

from mkmapdiary.lib.asset import AssetRecord
from mkmapdiary.postprocessors.base.singleAssetPostprocessor import (
    SingleAssetPostprocessor,
)


class EntropyCalculator(SingleAssetPostprocessor):
    @property
    def info(self) -> str:
        return "Calculating image entropy."

    def __init__(self, ai: Callable, config: dict) -> None:
        super().__init__(ai, config)
        self.__enabled = config["features"]["entropy_filtering"]["enabled"]

    @classmethod
    def filter(cls, asset: AssetRecord) -> bool:
        return asset.type == "image"

    def processSingleAsset(self, asset: AssetRecord) -> None:
        if not self.__enabled:
            asset.entropy = 8.0
            return

        resize = 256
        img = Image.open(asset.path).convert("L").resize((resize, resize))
        arr = np.asarray(img, dtype=np.float32)

        hist, _ = np.histogram(arr, bins=256, range=(0, 255))
        p = hist / np.sum(hist)
        p = p[p > 0]
        entropy = -np.sum(p * np.log2(p))
        asset.entropy = entropy
