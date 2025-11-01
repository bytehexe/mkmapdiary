from typing import Any, Dict, Iterator

import whenever
from doit import create_after

from .base.baseTask import BaseTask


class DayPageTask(BaseTask):
    def __init__(self) -> None:
        super().__init__()

    @create_after("gpx2gpx")
    def task_build_day_page(self) -> Iterator[Dict[str, Any]]:
        """Generate day pages for each date with assets."""

        def _generate_day_page(date: whenever.Date) -> None:
            formatter = "%a, %x"

            day_page_path = self.dirs.docs_dir / f"{date}.md"
            with open(day_page_path, "w") as f:
                formatted_date = date.py_date().strftime(
                    formatter,
                )
                f.write(
                    self.template(
                        "day_base.j2",
                        formatted_date=formatted_date,
                        journal_title=self.config["strings"]["journal_title"],
                        date=date,
                    ),
                )

        for date in self.db.get_all_dates():
            if date is None:
                continue

            yield dict(
                name=str(date),
                actions=[(_generate_day_page, (date,))],
                targets=[self.dirs.docs_dir / f"{date}.md"],
                task_dep=[f"create_directory:{self.dirs.docs_dir}"],
                uptodate=[True],
            )
