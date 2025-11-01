import pathlib
from typing import Any, Dict, Iterator

import whenever
from doit import create_after

from .base.baseTask import BaseTask


class TagsTask(BaseTask):
    def __init__(self) -> None:
        super().__init__()

    @create_after("gpx2gpx")
    def task_build_tags(self) -> Iterator[Dict[str, Any]]:
        """Generate tags list."""

        def _generate_tags(date: whenever.Date) -> None:
            tags_path = (
                self.dirs.docs_dir / "templates" / f"{date.format_iso()}_tags.md"
            )

            content = []

            for asset, asset_type in self.db.get_assets_by_date(
                date,
                ("markdown", "audio"),
            ):
                if asset_type == "audio":
                    asset = pathlib.Path(str(asset) + ".md")
                with open(asset) as f:
                    file_content_str = f.read()
                if asset_type == "audio":
                    # Remove first line (title)
                    content.append(file_content_str.split("\n", 1)[1])
                else:
                    # Remove raw text blocks
                    file_content_lines = file_content_str.split("\n")
                    file_content_lines = [
                        line
                        for line in file_content_lines
                        if not line.startswith("```")
                    ]
                    content.append("\n".join(file_content_lines))

            if content:
                language = self.config["site"]["locale"].split(".")[0]
                tags = self.ai(
                    "generate_tags",
                    dict(locale=language, text="\n\n".join(content)),
                )
            else:
                tags = ""

            with open(tags_path, "w") as f:
                f.write(
                    self.template(
                        "day_tags.j2",
                        tags=tags,
                    ),
                )

        for date in self.db.get_all_dates():
            yield dict(
                name=str(date),
                actions=[(_generate_tags, [date])],
                targets=[
                    self.dirs.docs_dir / "templates" / f"{date.format_iso()}_tags.md"
                ],
                file_dep=self.db.get_all_assets(),
                calc_dep=["get_gpx_deps"],
                task_dep=[
                    f"create_directory:{self.dirs.templates_dir}",
                    "transcribe_audio",
                ],
                uptodate=[True],
            )
