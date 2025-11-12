import logging

import imagehash
import numpy as np
from sklearn.cluster import AgglomerativeClustering

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

        # Group assets by display_date
        assets_by_date: dict[str, list[AssetRecord]] = {}
        for asset in assets:
            # Use string representation of display_date as key, handling None case
            date_key = str(asset.display_date) if asset.display_date else "no_date"
            if date_key not in assets_by_date:
                assets_by_date[date_key] = []
            assets_by_date[date_key].append(asset)

        # Process duplicate detection for each date group separately
        for date_key, date_assets in assets_by_date.items():
            if len(date_assets) <= 1:
                # Skip if only one asset for this date
                continue

            logger.debug(
                f"Processing duplicate detection for {len(date_assets)} images on {date_key}"
            )
            self._process_duplicates_for_date_group(date_assets)

    def _process_duplicates_for_date_group(self, assets: list[AssetRecord]) -> None:
        """Process duplicate detection for a group of assets from the same display date."""
        assets = [
            a
            for a in assets
            if a.image_hash is not None and a.timestamp_utc is not None
        ]
        hashes = [asset.image_hash for asset in assets]

        # Compute distance matrix
        distance_matrix = np.zeros((len(assets), len(assets)))
        for i in range(len(assets)):
            for j in range(i + 1, len(assets)):
                hash1: imagehash.ImageHash = hashes[i]  # type: ignore
                hash2: imagehash.ImageHash = hashes[j]  # type: ignore
                distance = abs(hash1 - hash2)
                time_distance = abs(
                    (assets[i].timestamp_utc - assets[j].timestamp_utc).in_minutes()  # type: ignore
                )
                distance_matrix[i][j] = distance + time_distance * 0.5
                distance_matrix[j][i] = distance + time_distance * 0.5

        logger.debug(
            f"Distance matrix properties: min={distance_matrix[distance_matrix > 0].min()}, max={distance_matrix.max()}, mean={distance_matrix.mean()}"
        )

        # Compute cluster
        threshold = 10
        clustering = AgglomerativeClustering(
            n_clusters=None,
            distance_threshold=threshold,
            metric="precomputed",
            linkage="complete",  # separate clusters more strictly
        )
        labels = clustering.fit_predict(distance_matrix)

        # Mark duplicates
        label_to_assets: dict[int, list[AssetRecord]] = {}
        for i, label in enumerate(labels):
            if label not in label_to_assets:
                label_to_assets[label] = []
            label_to_assets[label].append(assets[i])

        # Update asset metadata
        for _label, cluster_assets in label_to_assets.items():
            if len(cluster_assets) > 1:
                # Mark all assets in this cluster as duplicates, except the best one
                best_asset = max(cluster_assets, key=lambda a: a.quality or 0)
                for asset in cluster_assets:
                    if asset == best_asset:
                        asset.is_duplicate = False
                    else:
                        asset.is_duplicate = True
