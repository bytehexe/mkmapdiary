import pathlib
from collections.abc import Iterable, Iterator
from typing import Any

import whenever
from doit import create_after

from mkmapdiary.lib import aiUsage

from .base.baseTask import BaseTask


def journal_text(parts: Iterable[tuple[str, str]]) -> str:
    """Text handed to `generate_tags`, empty when there is nothing to tag.

    `parts` pairs each asset's type with the contents of its markdown file.
    Emptiness has to be decided on the joined text, not on the number of
    assets: an audio file built with `features.transcription` off leaves a .md
    holding only its heading, and dropping that heading leaves a bare newline.
    """
    content = []

    for asset_type, raw in parts:
        if asset_type == "audio":
            # Remove first line (title)
            _, _, body = raw.partition("\n")
            content.append(body)
        else:
            # Remove raw text blocks
            content.append(
                "\n".join(
                    line for line in raw.split("\n") if not line.startswith("```")
                ),
            )

    return "\n\n".join(content).strip()


class TagsTask(BaseTask):
    def __init__(self) -> None:
        super().__init__()

    @create_after("end_postprocessing")
    def task_build_tags(self) -> Iterator[dict[str, Any]]:
        """Generate tags list."""

        def _generate_tags(date: whenever.Date) -> None:
            tags_path = (
                self.dirs.docs_dir / "templates" / f"{date.format_iso()}_tags.md"
            )

            parts = []

            for asset in self.db.get_assets_by_date(
                date,
                ("markdown", "audio"),
            ):
                asset_path = asset.path
                if asset.type == "audio":
                    asset_path = pathlib.Path(str(asset.path) + ".md")
                with open(asset_path) as f:
                    parts.append((asset.type, f.read()))

            text = journal_text(parts)

            tags = ""
            if text:
                language = self.config["site"]["locale"].split(".")[0]
                tags = (
                    self.ai(
                        "generate_tags",
                        dict(locale=language, text=text),
                    )
                    or ""
                )

            self.record_ai_usage(str(date), [aiUsage.TAGS] if tags else [])

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
                    self.dirs.docs_dir / "templates" / f"{date.format_iso()}_tags.md",
                    self.ai_usage_path(str(date)),
                ],
                file_dep=[str(asset.path) for asset in self.db.get_all_assets()],
                calc_dep=["get_gpx_deps"],
                task_dep=[
                    f"create_directory:{self.dirs.templates_dir}",
                    "transcribe_audio",
                ],
                uptodate=[False],
            )
