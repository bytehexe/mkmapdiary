from .base.baseTask import BaseTask
from pathlib import PosixPath
from typing import Callable, Dict, Iterator, List, Tuple, Union, Any


class MarkdownTask(BaseTask):
    def __init__(self):
        super().__init__()
        self.__sources = []

    def handle_markdown(self, source):
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

    def task_markdown2markdown(self) -> Iterator[Dict[str, Any]]:
        """Copy text files to the assets directory."""

        def _to_md(src, dst):
            with open(src, "r") as f_src, open(dst, "w") as f_dst:
                content = f_src.readlines()

                # Check if there is a title
                if not content:
                    f_dst.write("")
                    return

                if not content[0].startswith("#"):
                    content.insert(0, f"# No Title\n")
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
