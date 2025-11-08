from collections.abc import Iterator
from pathlib import PosixPath
from typing import Any

from mkmapdiary.lib.asset import AssetRecord
from mkmapdiary.lib.calibration import Calibration

from .base.baseTask import BaseTask


class MarkdownTask(BaseTask):
    def __init__(self) -> None:
        super().__init__()
        self.__sources: list[PosixPath] = []

    def handle_markdown(
        self, source: PosixPath, calibration: Calibration
    ) -> Iterator[AssetRecord]:
        # Create task to convert image to target format
        self.__sources.append(source)

        yield AssetRecord(
            path=self.__generate_destination_filename(source),
            type="markdown",
            timestamp_utc=self.extract_meta_datetime(source, calibration),
        )

    def __generate_destination_filename(self, source: PosixPath) -> PosixPath:
        file_format = "md"
        filename = PosixPath(self.dirs.assets_dir / source.stem).with_suffix(
            f".{file_format}"
        )
        return self.make_unique_filename(source, filename)

    def task_markdown2markdown(self) -> Iterator[dict[str, Any]]:
        """Copy text files to the assets directory."""

        def _to_md(src: PosixPath, dst: PosixPath) -> None:
            with open(src) as f_src, open(dst, "w") as f_dst:
                content = f_src.readlines()

                # Check if there is a title
                if not content:
                    f_dst.write("")
                    return

                if content[0].startswith("#"):
                    content[0] = (
                        f"# {self.config['strings']['text_title']}: {content[0][1:]}"
                    )
                else:
                    content.insert(0, f"# {self.config['strings']['text_title']}\n")
                    content.insert(1, "\n")

                for i, line in enumerate(content):
                    if line.startswith("#"):
                        content[i] = "##" + line
                        break

                f_dst.write("".join(content))

        for src in self.__sources:
            dst = self.__generate_destination_filename(src)
            yield dict(
                name=dst,
                actions=[(_to_md, (src, dst))],
                file_dep=[src],
                task_dep=[f"create_directory:{dst.parent}"],
                targets=[dst],
            )
