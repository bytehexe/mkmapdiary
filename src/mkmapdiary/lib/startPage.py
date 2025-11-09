import logging
import math

import numpy as np
import sklearn.cluster
import sklearn.metrics.pairwise

from mkmapdiary.lib.asset import AssetRecord

logger = logging.getLogger(__name__)


class StartPage:
    def __init__(self, assets: list[AssetRecord], config: dict):
        self.assets = assets
        self.config = config

        valid_assets = [
            asset
            for asset in assets
            if not asset.is_duplicate
            and not asset.is_bad
            and asset.timestamp_utc is not None
        ]
        geo_assets = [
            asset
            for asset in valid_assets
            if asset.latitude is not None and asset.longitude is not None
        ]
        non_geo_assets = [
            asset
            for asset in valid_assets
            if asset.latitude is None or asset.longitude is None
        ]

        # Calculate mode
        if not geo_assets:
            self.with_map = False
            self.target_gallery_count = 24
            self.target_map_count = 0
            self.gallery_rows = 3
        else:
            self.with_map = True
            self.target_gallery_count = 8
            self.target_map_count = 10
            self.gallery_rows = 1

        # Ensure we don't request more map assets than available
        self.target_map_count = min(self.target_map_count, len(geo_assets))

        # Ensure we don't request more gallery assets than available
        self.target_gallery_count = min(
            self.target_gallery_count, len(valid_assets) - self.target_map_count
        )

        self.geo_portion = len(geo_assets) / len(valid_assets) if valid_assets else 0
        self.geo_bucket_size = max(
            math.ceil(self.total_target_count * self.geo_portion), self.target_map_count
        )
        self.non_geo_bucket_size = self.total_target_count - self.geo_bucket_size

        geo_bucket = self._calculate_bucket(
            geo_assets, self.geo_bucket_size, with_geo=True
        )
        non_geo_bucket = self._calculate_bucket(
            non_geo_assets,
            self.non_geo_bucket_size,
            with_geo=False,
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

    def _calculate_bucket(
        self,
        assets: list[AssetRecord],
        bucket_size: int,
        with_geo: bool,
        with_non_geo: bool = True,
    ) -> list[AssetRecord]:
        if len(assets) <= bucket_size:
            return assets

        if with_geo:
            geo_distance_matrix = self._calculate_geo_distance_matrix(assets)
        else:
            geo_distance_matrix = np.zeros((len(assets), len(assets)))

        if with_non_geo:
            color_distance_matrix = self._calculate_color_distance_matrix(assets)
            time_distance_matrix = self._calculate_time_distance_matrix(assets)
        else:
            color_distance_matrix = np.zeros((len(assets), len(assets)))
            time_distance_matrix = np.zeros((len(assets), len(assets)))

        total_distance_matrix = (
            geo_distance_matrix + color_distance_matrix + time_distance_matrix
        )

        # Continue with clustering
        return self._cluster_assets(bucket_size, assets, total_distance_matrix)

    @classmethod
    def _cluster_assets(
        cls, bucket_size: int, assets: list[AssetRecord], distance_matrix: np.ndarray
    ) -> list[AssetRecord]:
        if len(assets) <= bucket_size:
            return assets

        clustering = sklearn.cluster.AgglomerativeClustering(
            n_clusters=bucket_size, metric="precomputed", linkage="average"
        )
        labels = clustering.fit_predict(distance_matrix)

        clustered_assets = []
        for cluster_id in range(bucket_size):
            cluster_indices = np.where(labels == cluster_id)[0]
            cluster_assets = [assets[i] for i in cluster_indices]

            # Select the asset with the highest quality in the cluster
            best_asset = max(cluster_assets, key=lambda a: a.quality or 0)
            clustered_assets.append(best_asset)

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
