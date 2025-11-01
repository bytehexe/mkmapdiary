from pathlib import PosixPath
from typing import Any, Dict, Generator, Iterator

import imageio.v2 as imageio
import rawpy

from .base.exifReader import ExifReader
from .imageTask import ImageTask


class Cr2Task(ImageTask, ExifReader):
    def __init__(self) -> None:
        super().__init__()
        self.__sources: list[PosixPath] = []

    def __generate_intermediate_filename(self, source: PosixPath) -> PosixPath:
        filename = PosixPath(self.dirs.files_dir / source.stem).with_suffix(".jpeg")
        return self.make_unique_filename(source, filename)

    def handle_ext_cr2(self, source: PosixPath) -> Generator:
        self.__sources.append(source)
        intermediate_file = self.__generate_intermediate_filename(source)
        assets = list(self.handle_image(intermediate_file))

        assert len(assets) == 1
        asset = assets[0]

        asset.meta.update(self.read_exif(source))
        yield asset

    def task_convert_raw(self) -> Iterator[Dict[str, Any]]:
        """Convert a RAW image to JPEG."""

        def _convert(src: PosixPath, dst: PosixPath) -> None:
            with rawpy.imread(str(src)) as raw:
                rgb = raw.postprocess(
                    use_camera_wb=True,  # Kamera-Weißabgleich
                    no_auto_bright=False,  # automatische Helligkeit
                    output_bps=8,  # 8-bit pro Kanal (statt 16)
                )
            imageio.imwrite(dst, rgb)

        for src in self.__sources:
            dst = self.__generate_intermediate_filename(src)
            yield dict(
                name=dst,
                actions=[(_convert, (src, dst))],
                file_dep=[src],
                targets=[dst],
                task_dep=[f"create_directory:{dst.parent}"],
            )
