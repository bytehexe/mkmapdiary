from typing import Any

from doit import create_after

from mkmapdiary.tasks.base.baseTask import BaseTask


class PostprocessingTask(BaseTask):
    def __init__(self) -> None:
        super().__init__()

    @create_after("end_gpx")
    def task_post_processing(self) -> dict[str, Any]:
        """Perform post-processing after GPX processing."""

        def _post_process() -> None:
            # Implement post-processing logic here
            pass

        return {
            "actions": [_post_process],
            "task_dep": ["end_gpx"],
            "uptodate": [False],
        }

    def task_end_postprocessing(self) -> dict[str, Any]:
        return {
            "actions": [],
            "task_dep": ["post_processing"],
        }
