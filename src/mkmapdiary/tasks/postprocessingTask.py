import gc
import logging
from collections.abc import Iterator
from typing import Any

from doit import create_after
from tabulate import tabulate

from mkmapdiary.lib.asset import AssetRecord
from mkmapdiary.postprocessors.base.multiAssetPostprocessor import (
    MultiAssetPostprocessor,
)
from mkmapdiary.postprocessors.base.singleAssetPostprocessor import (
    SingleAssetPostprocessor,
)
from mkmapdiary.postprocessors.duplicateDetector import DuplicateDetector
from mkmapdiary.postprocessors.entropyCalculator import EntropyCalculator
from mkmapdiary.postprocessors.imageHasher import ImageHasher
from mkmapdiary.postprocessors.imageQualityAssessment import ImageQualityAssessment
from mkmapdiary.tasks.base.baseTask import BaseTask
from mkmapdiary.util.log import ThisMayTakeAWhile

logger = logging.getLogger(__name__)


class PostprocessingTask(BaseTask):
    def __init__(self) -> None:
        super().__init__()

    @create_after("end_gpx")
    def task_post_processing_single(self) -> Iterator[dict[str, Any]]:
        """Perform post-processing after GPX processing."""

        def __process(
            processor_class: type[SingleAssetPostprocessor], asset: AssetRecord
        ) -> None:
            processor = processor_class(self.ai, self.config)
            processor.processSingleAsset(asset)

        # All single-asset postprocessors. Single-asset postprocessors process each asset individually.
        # They should be used for tasks that can be multithreaded and do not depend on previous postprocessing steps.
        # Single-asset postprocessors are guaranteed to run before any multi-asset postprocessors but
        # their order among each other is completely arbitrary.
        postprocessors: list[type[SingleAssetPostprocessor]] = [
            ImageHasher,
            EntropyCalculator,
        ]

        for processor_class in postprocessors:
            for asset in self.db.assets:
                if not processor_class.filter(asset):
                    continue
                yield {
                    "name": f"{processor_class.__name__}_{asset.path.stem}_{asset.id}",
                    "actions": [(__process, (processor_class, asset))],
                    "task_dep": ["end_gpx"],
                    "uptodate": [False],
                }

    @create_after("post_processing_single")
    def task_post_processing(self) -> dict[str, Any]:
        """Perform post-processing after GPX processing."""

        def __process() -> None:
            # All multi-asset postprocessors. Multi-asset postprocessors can access all assets.
            # They should be used for tasks that require context from multiple assets, or that
            # cannot be multithreaded or depend on previous postprocessing steps.
            # Multi-asset postprocessors are guaranteed to run after all single-asset postprocessors and
            # in the order they are listed here.
            # In particular, AI tasks cannot be multithreaded due to thread-safety and memory constraints.
            postprocessors: list[type[MultiAssetPostprocessor]] = [
                ImageQualityAssessment,
                DuplicateDetector,
                # JournalSummarizer,
                # ImageSummarizer,
                # ImageEmbedder,
            ]

            for processor_class in postprocessors:
                self.__gc()
                processor = processor_class(self.ai, self.config)
                with ThisMayTakeAWhile(logger, processor.info, icon="🛠️"):
                    processor.processAllAssets(self.db.assets)
                    self.__gc()

        return {
            "actions": [__process],
            "task_dep": ["post_processing_single", "end_gpx"],
            "uptodate": [False],
        }

    def __gc(self) -> None:
        gc.collect()
        try:
            import torch
        except ImportError:
            return
        torch.cuda.empty_cache()

    def task_end_postprocessing(self) -> dict[str, Any]:
        return {
            "actions": [self.__debug_db],
            "task_dep": ["post_processing"],
            "uptodate": [False],
        }

    def __debug_db(self) -> None:
        logger.debug("Assets after postprocessing:\n" + tabulate(*self.db.dump()))
