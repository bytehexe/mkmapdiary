
from .base.baseTask import BaseTask
import shutil

class TextTask(BaseTask):
    def __init__(self):
        super().__init__()
        self.__sources = []

    def handle_plain_text(self, source):
        # Create task to convert image to target format
        self.__sources.append(source)

        yield self.Asset(
            self.__generate_destination_filename(source),
            "text",
            {
                "date": self.extract_meta_datetime(source)
            }
        )
    
    def __generate_destination_filename(self, source):
        format = "txt"
        filename = (self.assets_dir / source.stem).with_suffix(f".{format}")
        return self.make_unique_filename(source, filename)

    def task_copy_text(self):
        """Copy text files to the assets directory."""

        
        def _copy(src, dst):
            shutil.copy2(src, dst)

        for src in self.__sources:
            dst = self.__generate_destination_filename(src)
            yield dict(
                    name=dst,
                    actions=[(_copy, (src, dst))],
                    file_dep=[src],
                    task_dep=[f"create_directory:{dst.parent}"],
                    targets=[dst],
                )