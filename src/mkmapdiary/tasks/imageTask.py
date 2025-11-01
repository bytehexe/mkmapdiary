from pathlib import PosixPath
from typing import Any, Dict, Iterator

from PIL import Image

from mkmapdiary.lib.asset import AssetRecord

from .base.baseTask import BaseTask
from .base.exifReader import ExifReader


class ImageTask(BaseTask, ExifReader):
    def __init__(self) -> None:
        super().__init__()
        self.__sources: list[PosixPath] = []

    def handle_image(self, source: PosixPath) -> Iterator[AssetRecord]:
        # Create task to convert image to target format
        self.__sources.append(source)

        exif_data = self.read_exif(source)

        asset = AssetRecord(
            path=self.__generate_destination_filename(source),
            type="image",
            timestamp_utc=exif_data.create_date,
            latitude=exif_data.latitude,
            longitude=exif_data.longitude,
        )

        yield asset

    def __generate_destination_filename(self, source: PosixPath) -> PosixPath:
        image_format = self.config.get("image_format", "jpg")
        filename = PosixPath(self.dirs.assets_dir / source.stem).with_suffix(
            f".{image_format}"
        )
        return self.make_unique_filename(source, filename)

    def task_convert_image(self) -> Iterator[Dict[str, Any]]:
        """Convert an image to a different format."""

        def _convert(src: PosixPath, dst: PosixPath) -> None:
            with Image.open(src) as img:
                # apply image orientation if needed
                orientation = self.read_exif(src).orientation
                if orientation == 3:
                    img = img.rotate(180, expand=True)
                elif orientation == 6:
                    img = img.rotate(270, expand=True)
                elif orientation == 8:
                    img = img.rotate(90, expand=True)

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
