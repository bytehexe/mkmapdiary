from .base.baseTask import BaseTask
from doit import create_after
from pathlib import PosixPath
from typing import Callable, Dict, Iterator, List, Tuple, Union, Any


class TagsTask(BaseTask):
    def __init__(self):
        super().__init__()

    @create_after("gpx2gpx")
    def task_build_tags(self) -> Iterator[Dict[str, Any]]:
        """Generate tags list."""

        def _generate_tags(date):
            tags_path = self.docs_dir / "templates" / f"{date}_tags.md"

            content = []

            for asset, asset_type in self.db.get_assets_by_date(
                date, ("markdown", "audio")
            ):
                if asset_type == "audio":
                    asset = str(asset) + ".md"
                with open(asset, "r") as f:
                    file_content = f.read()
                if asset_type == "audio":
                    # Remove first line (title)
                    content.append(file_content.split("\n", 1)[1])
                else:
                    # Remove raw text blocks
                    file_content = file_content.split("\n")
                    file_content = [
                        line for line in file_content if not line.startswith("```")
                    ]
                    content.append("\n".join(file_content))

            if content:
                tags = self.ai(
                    "generate_tags",
                    format=dict(
                        locale=self.config["locale"], text="\n\n".join(content)
                    ),
                )
            else:
                tags = ""

            with open(tags_path, "w") as f:
                f.write(
                    self.template(
                        "day_tags.j2",
                        tags=tags,
                    )
                )

        for date in self.db.get_all_dates():
            yield dict(
                name=str(date),
                actions=[(_generate_tags, [date])],
                targets=[self.docs_dir / "templates" / f"{date}_tags.md"],
                file_dep=self.db.get_all_assets(),
                calc_dep=["get_gpx_deps"],
                task_dep=[
                    f"create_directory:{self.templates_dir}",
                    "transcribe_audio",
                ],
                uptodate=[True],
            )
