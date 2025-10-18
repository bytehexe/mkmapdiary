from .base.baseTask import BaseTask

class JournalTask(BaseTask):
    def __init__(self):
        super().__init__()
    
    def task_build_journal(self):
        """Generate journal pages."""

        def _generate_journal(date):
            gallery_path = self.docs_dir / "templates" / f"{date}_journal.md"

            with open(gallery_path, "w") as f:
                f.write(self.template(
                    "day_journal.j2",
                    gallery_title = self.config["journal_title"],
                ))

        for date in self.db.get_all_dates():
            yield dict(
                name=str(date),
                actions=[(_generate_journal, [date])],
                targets=[self.docs_dir / "templates" / f"{date}_journal.md"],
                file_dep=self.db.get_all_assets(),
                task_dep=[f"create_directory:{self.templates_dir}"],
                uptodate=[True],
            )