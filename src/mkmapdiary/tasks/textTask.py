from pathlib import PosixPath
from typing import Any, Dict, Iterator

from mkmapdiary.lib.asset import Asset, AssetMeta

from .base.baseTask import BaseTask


class TextTask(BaseTask):
    def __init__(self) -> None:
        super().__init__()
        self.__sources: list[PosixPath] = []

    def handle_plain_text(self, source):
        # Create task to convert image to target format
        self.__sources.append(source)

        yield Asset(
            self.__generate_destination_filename(source),
            "markdown",
            AssetMeta(timestamp=self.extract_meta_datetime(source)),
        )

    def __generate_destination_filename(self, source):
        file_format = "md"
        filename = (self.dirs.assets_dir / source.stem).with_suffix(f".{file_format}")
        return self.make_unique_filename(source, filename)

    def task_text2markdown(self) -> Iterator[Dict[str, Any]]:
        """Copy text files to the assets directory."""

        def _to_md(src, dst) -> None:
            with open(src) as f_src, open(dst, "w") as f_dst:
                content = f_src.read()
                text = content.strip()

                title = f"{self.config['strings']['text_title']}: "
                title += self.ai(
                    "generate_title",
                    dict(locale=self.config["site"]["locale"], text=text),
                )

                markdown = self.template(
                    "md_text.j2",
                    title=title,
                    text=text,
                )

                f_dst.write(markdown)

        for src in self.__sources:
            dst = self.__generate_destination_filename(src)
            yield dict(
                name=dst,
                actions=[(_to_md, (src, dst))],
                file_dep=[src],
                task_dep=[f"create_directory:{dst.parent}"],
                targets=[dst],
            )
