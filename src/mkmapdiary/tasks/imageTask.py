from PIL import Image
from .base.baseTask import BaseTask
from .base.exifReader import ExifReader
from pathlib import PosixPath
from typing import Callable, Dict, Iterator, List, Tuple, Union, Any


class ImageTask(BaseTask, ExifReader):
    def __init__(self):
        super().__init__()
        self.__sources = []

    def handle_image(self, source):
        # Create task to convert image to target format
        self.__sources.append(source)

        meta = {}
        meta.update(self.read_exif(source))

        yield self.Asset(self.__generate_destination_filename(source), "image", meta)

    def __generate_destination_filename(self, source):
        format = self.config.get("image_format", "jpg")
        filename = (self.assets_dir / source.stem).with_suffix(f".{format}")
        return self.make_unique_filename(source, filename)

    def task_convert_image(self) -> Iterator[Dict[str, Any]]:
        """Convert an image to a different format."""

        def _convert(src, dst):
            with Image.open(src) as img:
                img.convert("RGB").save(dst, **self.config.get("image_options", {}))

        for src in self.__sources:
            dst = self.__generate_destination_filename(src)
            yield dict(
                name=dst,
                actions=[(_convert, (src, dst))],
                file_dep=[src],
                task_dep=[f"create_directory:{dst.parent}"],
                targets=[dst],
            )
