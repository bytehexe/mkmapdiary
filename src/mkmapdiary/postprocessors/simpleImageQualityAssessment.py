import logging
from pathlib import Path

import numpy as np
from PIL import Image
from scipy.ndimage import laplace

from mkmapdiary.lib.asset import AssetRecord
from mkmapdiary.postprocessors.base.multiAssetPostprocessor import (
    MultiAssetPostprocessor,
)

logger = logging.getLogger(__name__)


class SimpleImageQualityAssessment(MultiAssetPostprocessor):
    @property
    def info(self) -> str:
        return "Assessing image quality."

    def processAllAssets(self, assets: list[AssetRecord]) -> None:
        image_paths = [asset.path for asset in assets if asset.type == "image"]
        if not image_paths:
            return

        scores = self.compute_iqa_scores(image_paths)

        stddev = np.std(list(scores.values()))
        mean = np.mean(list(scores.values()))
        threshold = mean - 2 * stddev

        logger.debug(
            f"IQA scores: mean={mean:.3f}, stddev={stddev:.3f}, threshold for low quality={threshold:.3f}"
        )

        for asset in assets:
            if asset.type == "image":
                asset.quality = scores.get(asset.path, None)
                if asset.quality is not None and asset.quality < threshold:
                    asset.is_bad = True

    @classmethod
    def compute_raw_metrics(
        cls, image_paths: list[Path]
    ) -> tuple[np.ndarray, np.ndarray]:
        """Compute raw Laplacian variance and contrast for each image."""
        laplacians = []
        contrasts = []

        for path in image_paths:
            img = Image.open(path).convert("L")
            img.thumbnail((1024, 1024))
            arr = np.array(img, dtype=np.float32) / 255.0

            laplacians.append(laplace(arr).var())
            contrasts.append(np.std(arr))

        return np.array(laplacians), np.array(contrasts)

    @classmethod
    def normalize_vector(
        cls, vec: np.ndarray, min_val: float | None = None, max_val: float | None = None
    ) -> np.ndarray:
        """Normalize a vector to [0,1]."""
        if min_val is None:
            min_val = vec.min()
        if max_val is None:
            max_val = vec.max()
        normalized = (vec - min_val) / (max_val - min_val)
        return np.clip(normalized, 0.0, 1.0)

    @classmethod
    def compute_iqa_scores(cls, image_paths: list[Path]) -> dict[Path, float]:
        """Compute combined normalized IQA scores for all images in a folder."""

        if not image_paths:
            raise ValueError("No images found in folder.")

        # Compute raw metrics
        lap_scores, contrast_scores = cls.compute_raw_metrics(image_paths)

        # Normalize each metric individually
        lap_norm = cls.normalize_vector(lap_scores)
        contrast_norm = cls.normalize_vector(contrast_scores)
        # Combine equally
        combined_scores = 0.5 * lap_norm + 0.5 * contrast_norm

        # Prepare results
        results = {
            path: float(score)
            for path, score in zip(image_paths, combined_scores, strict=False)
        }

        return results
