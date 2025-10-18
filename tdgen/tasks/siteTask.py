from .baseTask import BaseTask

class SiteTask(BaseTask):
    def __init__(self):
        super().__init__()
    
    @property
    def __site_dirs(self):
        return [
            self.build_dir,
            self.assets_dir,
        ]

    def task_create_directory(self):
        """Create a directory if it doesn't exist."""

        def _create_directory():
            dir.mkdir(parents=True, exist_ok=True)

        for dir in self.__site_dirs:
            yield dict(
                    name=dir,
                    actions=[_create_directory],
                    targets=[dir],
                )