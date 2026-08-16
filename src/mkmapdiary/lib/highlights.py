import logging
import math
import pathlib
from collections.abc import Iterable

import numpy as np
import sklearn.cluster
import sklearn.metrics.pairwise
from scipy.optimize import dual_annealing

from mkmapdiary.lib.asset import AssetRecord

logger = logging.getLogger(__name__)


def resolve_pinned_highlights(
    configured: list[str],
    source_dir: pathlib.Path,
    assets: list[AssetRecord],
    sources: Iterable[tuple[pathlib.Path, pathlib.Path]],
) -> list[AssetRecord]:
    """Turn configured source paths into the assets they were converted into.

    ``sources`` pairs an asset path with the source file it came from, which is
    what lets the configuration name ``day1/IMG_1234.CR2`` while the page shows
    ``IMG_1234.jpg``.
    """

    by_source = {source: destination for destination, source in sources}
    by_path = {asset.path: asset for asset in assets}

    pinned = []
    for entry in configured:
        source = source_dir / entry
        destination = by_source.get(source)
        asset = by_path.get(destination) if destination is not None else None
        if asset is None:
            raise ValueError(
                f"Configured highlight {entry!r} does not match any image "
                f"below {source_dir}"
            )
        pinned.append(asset)

    return pinned


class Highlights:
    def __init__(
        self,
        assets: list[AssetRecord],
        config: dict,
        day_page: bool = False,
        pinned: list[AssetRecord] | None = None,
    ):
        self.assets = assets
        self.config = config
        # An explicit choice outranks the heuristics, so pinned assets skip the
        # duplicate, quality and entropy filters entirely.
        self.pinned = list(pinned or [])

        valid_assets = self.pinned + [
            asset
            for asset in assets
            if asset not in self.pinned
            and not asset.is_duplicate
            and not asset.is_bad
            and asset.timestamp_utc is not None
            and asset.entropy is not None
            and asset.entropy > 6.5
        ]
        # Pinned assets lead the highlight strip, so they never compete for one
        # of the map markers, whether or not they carry coordinates.
        geo_assets = [
            asset
            for asset in valid_assets
            if asset not in self.pinned
            and asset.latitude is not None
            and asset.longitude is not None
        ]
        non_geo_assets = [
            asset
            for asset in valid_assets
            if asset in self.pinned or asset.latitude is None or asset.longitude is None
        ]

        # Calculate mode
        if not geo_assets:
            self.with_map = False
            if day_page:
                self.target_gallery_count = 8
            else:
                self.target_gallery_count = 24
            self.target_map_count = 0
            self.gallery_rows = 3
        else:
            self.with_map = True
            self.target_gallery_count = 8
            if day_page:
                self.target_map_count = 0
            else:
                self.target_map_count = 10
            self.gallery_rows = 1

        # Ensure we don't request more map assets than available
        self.target_map_count = min(self.target_map_count, len(geo_assets))

        # Ensure we don't request more gallery assets than available
        self.target_gallery_count = min(
            self.target_gallery_count, len(valid_assets) - self.target_map_count
        )
        # Every pin is shown, even when they outnumber the usual strip.
        self.target_gallery_count = max(self.target_gallery_count, len(self.pinned))

        self.geo_portion = len(geo_assets) / len(valid_assets) if valid_assets else 0
        # Capping at the pin-free remainder keeps room for the pins, which all
        # live in the non-geo bucket. target_map_count fits either way, because
        # target_gallery_count is at least the number of pins.
        self.geo_bucket_size = min(
            max(
                math.ceil(self.total_target_count * self.geo_portion),
                self.target_map_count,
            ),
            self.total_target_count - len(self.pinned),
        )
        self.non_geo_bucket_size = self.total_target_count - self.geo_bucket_size

        geo_bucket = self._calculate_bucket(
            geo_assets, self.geo_bucket_size, with_geo=True
        )
        non_geo_bucket = self._calculate_bucket(
            non_geo_assets,
            self.non_geo_bucket_size,
            with_geo=False,
            pinned=self.pinned,
        )

        logger.debug(f"Valid assets count: {len(valid_assets)}")
        logger.debug(f"Geo assets count: {len(geo_assets)}")
        logger.debug(f"Non-geo assets count: {len(non_geo_assets)}")
        logger.debug(f"Geo portion: {self.geo_portion}")
        logger.debug(f"Total target count: {self.total_target_count}")
        logger.debug(f"Target gallery count: {self.target_gallery_count}")
        logger.debug(f"Target map count: {self.target_map_count}")
        logger.debug(f"Geo bucket size: {self.geo_bucket_size}")
        logger.debug(f"Non-geo bucket size: {self.non_geo_bucket_size}")

        assert len(geo_bucket) <= self.geo_bucket_size
        assert len(non_geo_bucket) <= self.non_geo_bucket_size
        assert self.target_map_count <= self.geo_bucket_size

        # Further reduce the geo bucket
        self.map_assets = self._calculate_bucket(
            geo_bucket,
            self.target_map_count,
            with_geo=True,
            with_non_geo=False,
        )

        # Add assets from the geo bucket not selected for the map to the non-geo bucket
        remaining_geo_assets = [
            asset for asset in geo_bucket if asset not in self.map_assets
        ]
        non_geo_bucket.extend(remaining_geo_assets)
        self.gallery_assets = non_geo_bucket

        assert len(self.gallery_assets) == self.target_gallery_count
        assert len(self.map_assets) == self.target_map_count

        self.map_assets.sort(key=lambda a: a.quality or 0)
        self._arrange_gallery_assets(self.gallery_assets, pinned=self.pinned)

    def _calculate_bucket(
        self,
        assets: list[AssetRecord],
        bucket_size: int,
        with_geo: bool,
        with_non_geo: bool = True,
        pinned: list[AssetRecord] | None = None,
    ) -> list[AssetRecord]:
        if len(assets) <= bucket_size:
            return assets

        total_distance_matrix = self._calculate_distance_matrix(
            assets, with_geo=with_geo, with_non_geo=with_non_geo
        )

        # Continue with clustering
        return self._cluster_assets(
            bucket_size, assets, total_distance_matrix, pinned=pinned
        )

    @classmethod
    def _calculate_distance_matrix(
        cls, assets: list[AssetRecord], with_geo: bool, with_non_geo: bool
    ) -> np.ndarray:
        if with_geo:
            geo_distance_matrix = cls._calculate_geo_distance_matrix(assets)
        else:
            geo_distance_matrix = np.zeros((len(assets), len(assets)))

        if with_non_geo:
            color_distance_matrix = cls._calculate_color_distance_matrix(assets)
            time_distance_matrix = cls._calculate_time_distance_matrix(assets)
        else:
            color_distance_matrix = np.zeros((len(assets), len(assets)))
            time_distance_matrix = np.zeros((len(assets), len(assets)))

        total_distance_matrix = (
            geo_distance_matrix + color_distance_matrix + time_distance_matrix
        )

        return total_distance_matrix

    @classmethod
    def _cluster_assets(
        cls,
        bucket_size: int,
        assets: list[AssetRecord],
        distance_matrix: np.ndarray,
        pinned: list[AssetRecord] | None = None,
    ) -> list[AssetRecord]:
        pinned = pinned or []
        if len(assets) <= bucket_size:
            return assets
        if bucket_size == 0:
            return []

        clustering = sklearn.cluster.AgglomerativeClustering(
            n_clusters=bucket_size, metric="precomputed", linkage="average"
        )
        labels = clustering.fit_predict(distance_matrix)

        clustered_assets = []
        for cluster_id in range(bucket_size):
            cluster_indices = np.where(labels == cluster_id)[0]
            cluster_assets = [assets[i] for i in cluster_indices]

            # A pinned asset takes its whole cluster, so the near-identical
            # pictures grouped with it cannot be selected on their own merit.
            cluster_pins = [asset for asset in cluster_assets if asset in pinned]
            if cluster_pins:
                clustered_assets.extend(cluster_pins)
                continue

            # Select the asset with the highest quality in the cluster
            best_asset = max(cluster_assets, key=lambda a: a.quality or 0)
            clustered_assets.append(best_asset)

        # Clusters holding more than one pin overshoot the bucket. The pins are
        # not negotiable, so the weakest automatic picks yield their slots.
        while len(clustered_assets) > bucket_size:
            automatic = [a for a in clustered_assets if a not in pinned]
            if not automatic:
                break
            clustered_assets.remove(min(automatic, key=lambda a: a.quality or 0))

        return clustered_assets

    @classmethod
    def _calculate_time_distance_matrix(cls, assets: list[AssetRecord]) -> np.ndarray:
        # Calculate with numpy for efficiency
        if not assets:
            return np.array([]).reshape(0, 0)

        assert all([asset.timestamp_utc is not None for asset in assets]), (
            "All assets must have a valid timestamp_utc for time distance matrix calculation."
        )

        # Extract timestamps (we've already asserted they are not None)
        timestamps = np.array(
            [asset.timestamp_utc.timestamp() for asset in assets]  # type: ignore
        ).reshape(-1, 1)
        distance_matrix = sklearn.metrics.pairwise.pairwise_distances(timestamps)

        # Normalize the distance matrix
        return cls._norm(distance_matrix)

    @classmethod
    def _calculate_geo_distance_matrix(cls, assets: list[AssetRecord]) -> np.ndarray:
        # Calculate with numpy for efficiency
        if not assets:
            return np.array([]).reshape(0, 0)

        # Ensure all assets have valid coordinates
        assert all(
            asset.latitude is not None and asset.longitude is not None
            for asset in assets
        ), (
            "All assets must have valid latitude and longitude for geo distance matrix calculation."
        )

        coords = np.array(
            [
                [np.radians(asset.latitude), np.radians(asset.longitude)]  # type: ignore
                for asset in assets
            ]
        ).reshape(-1, 2)
        distance_matrix = sklearn.metrics.pairwise.haversine_distances(coords)

        # Normalize the distance matrix
        return cls._norm(distance_matrix)

    @classmethod
    def _calculate_color_distance_matrix(cls, assets: list[AssetRecord]) -> np.ndarray:
        if not assets:
            return np.array([]).reshape(0, 0)

        # Calculate Hamming distances between color hashes manually
        # since pairwise_distances doesn't work with ImageHash objects
        distance_matrix = np.zeros((len(assets), len(assets)))
        for i in range(len(assets)):
            for j in range(i + 1, len(assets)):
                hash1 = assets[i].color_hash
                hash2 = assets[j].color_hash
                if hash1 is not None and hash2 is not None:
                    distance = float(abs(hash1 - hash2))  # Hamming distance as float
                else:
                    # If either hash is None, use maximum distance
                    distance = 64.0  # Typical hash size for colorhash
                distance_matrix[i][j] = distance
                distance_matrix[j][i] = distance

        # Normalize the distance matrix
        return cls._norm(distance_matrix)

    @staticmethod
    def _norm(distance_matrix: np.ndarray) -> np.ndarray:
        if distance_matrix.size == 0:
            return distance_matrix

        min_val = distance_matrix.min()
        max_val = distance_matrix.max()
        assert isinstance(min_val, float) and isinstance(max_val, float)
        val_range = max_val - min_val
        if val_range == 0:
            val_range = 1
        # Avoid division by zero
        normalized_matrix = (distance_matrix - min_val) / val_range
        assert normalized_matrix.min() >= 0.0 and normalized_matrix.max() <= 1.0
        return normalized_matrix

    @property
    def total_target_count(self) -> int:
        return self.target_gallery_count + self.target_map_count

    @classmethod
    def _arrange_gallery_assets(
        cls,
        gallery_assets: list[AssetRecord],
        pinned: list[AssetRecord] | None = None,
    ) -> None:
        """Arrange gallery assets to alternate between high and low quality."""

        # The configured order is the user's, so the pins are placed rather than
        # arranged; only the automatic remainder goes through the optimiser.
        leading = [asset for asset in (pinned or []) if asset in gallery_assets]
        automatic = [asset for asset in gallery_assets if asset not in leading]

        if len(automatic) <= 2:
            gallery_assets.clear()
            gallery_assets.extend(leading + automatic)
            return

        distance_matrix = cls._calculate_distance_matrix(
            automatic, with_geo=False, with_non_geo=True
        )

        # Invert the distance matrix to get similarity matrix
        similarity_matrix = distance_matrix.max() - distance_matrix

        # Target function
        def _tour_length(order: np.ndarray) -> float:
            """Calculate the total distance of the tour given an order of assets."""
            order = np.argsort(order)  # reelle Werte → Permutation
            return np.sum(similarity_matrix[order, np.roll(order, -1)])

        # Dual annealing to arrange assets
        bounds = [(0, 1)] * len(automatic)

        result = dual_annealing(_tour_length, bounds, seed=42)
        initial_order = np.argsort(result.x)
        # initial_distance = np.sum(similarity_matrix[initial_order, np.roll(initial_order, -1)])

        # Apply initial arrangement
        arranged_assets = [automatic[i] for i in initial_order]

        # Rotate to put best asset in second position. With pins in front the
        # lead is already chosen, so the rotation would only displace them.
        if not leading:
            best_asset_index = max(
                range(len(arranged_assets)),
                key=lambda i: arranged_assets[i].quality or 0,
            )
            rotate_by = (best_asset_index - 1) % len(arranged_assets)
            arranged_assets = arranged_assets[rotate_by:] + arranged_assets[:rotate_by]

        gallery_assets.clear()
        gallery_assets.extend(leading + arranged_assets)
