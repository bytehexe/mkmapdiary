import logging

import imagehash
import numpy as np
from sklearn.cluster import DBSCAN

from mkmapdiary.lib.asset import AssetRecord
from mkmapdiary.postprocessors.base.multiAssetPostprocessor import (
    MultiAssetPostprocessor,
)

logger = logging.getLogger(__name__)


class DuplicateDetector(MultiAssetPostprocessor):
    @property
    def info(self) -> str:
        return "Detecting duplicate assets"

    def processAllAssets(self, assets: list[AssetRecord]) -> None:
        assets = [x for x in assets if x.type == "image"]
        hashes = [asset.image_hash for asset in assets]

        # Compute distance matrix
        distance_matrix = np.zeros((len(assets), len(assets)))
        for i in range(len(assets)):
            for j in range(i + 1, len(assets)):
                hash1: imagehash.ImageHash = hashes[i]  # type: ignore
                hash2: imagehash.ImageHash = hashes[j]  # type: ignore
                distance = abs(hash1 - hash2)
                distance_matrix[i][j] = distance
                distance_matrix[j][i] = distance

        logger.debug(
            "Distance matrix for duplicate detection:\n" + str(distance_matrix)
        )

        # Compute cluster
        threshold = 20
        clustering = DBSCAN(eps=threshold, min_samples=1, metric="precomputed")
        labels = clustering.fit_predict(distance_matrix)

        # Mark duplicates
        label_to_assets: dict[int, list[AssetRecord]] = {}
        for i, label in enumerate(labels):
            if label not in label_to_assets:
                label_to_assets[label] = []
            label_to_assets[label].append(assets[i])

        # Update asset metadata
        for _label, assets in label_to_assets.items():
            if len(assets) > 1:
                # Mark all assets in this cluster as duplicates, except the first one
                # TODO: Improve selection of best asset
                for asset in assets[1:]:
                    asset.duplicate = True
