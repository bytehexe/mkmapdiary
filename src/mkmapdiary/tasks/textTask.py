from .base.baseTask import BaseTask
import shutil
from pathlib import PosixPath
from typing import Callable, Dict, Iterator, List, Tuple, Union, Any


class TextTask(BaseTask):
    def __init__(self):
        super().__init__()
        self.__sources = []

    def handle_plain_text(self, source):
        # Create task to convert image to target format
        self.__sources.append(source)

        yield self.Asset(
            self.__generate_destination_filename(source),
            "markdown",
            {"date": self.extract_meta_datetime(source)},
        )

    def __generate_destination_filename(self, source):
        format = "md"
        filename = (self.assets_dir / source.stem).with_suffix(f".{format}")
        return self.make_unique_filename(source, filename)

    def task_text2markdown(self) -> Iterator[Dict[str, Any]]:
        """Copy text files to the assets directory."""

        def _to_md(src, dst):
            with open(src, "r") as f_src, open(dst, "w") as f_dst:
                content = f_src.readlines()

                title = content[0].strip() if content else "No Title"
                text = "".join(content[1:]).strip() if len(content) > 1 else ""

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
