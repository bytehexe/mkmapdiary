from .base.baseTask import BaseTask
import datetime
import pathlib

class DayPageTask(BaseTask):
    def __init__(self):
        super().__init__()
    
    def task_build_day_page(self):
        """Generate day pages for each date with assets."""
        
        def _generate_day_page(date):
            day_page_path = self.docs_dir / f"{date}.md"
            with open(day_page_path, "w") as f:
                formatted_date = datetime.datetime.strptime(date, "%Y-%m-%d").strftime("%x")
                f.write(self.template(
                    "day_base.j2",
                    formatted_date = formatted_date,
                    map_title = self.config["map_title"],
                    journal_title = self.config["journal_title"],
                    date = date,
                ))
        
        for date in self.db.get_all_dates():
            yield dict(
                name=str(date),
                actions=[(_generate_day_page, (date,))],
                targets=[self.docs_dir / f"{date}.md"],
                task_dep=[f"create_directory:{self.docs_dir}"],
                uptodate=[True],
            )

    def task_build_gallery(self):
        """Generate gallery pages."""
        # This is a placeholder for actual gallery generation logic
        def _generate_gallery(date):
            gallery_path = self.docs_dir / "templates" / f"{date}_gallery.md"

            gallery_items = []
            for asset in self.db.get_assets_by_date(date):
                item = dict(
                    basename = pathlib.PosixPath(asset).name,
                )
                gallery_items.append(item)

            with open(gallery_path, "w") as f:
                f.write(self.template(
                    "day_gallery.j2",
                    gallery_title = self.config["gallery_title"],
                    gallery_items = gallery_items,
                ))

        for date in self.db.get_all_dates():
            yield dict(
                name=str(date),
                actions=[(_generate_gallery, [date])],
                targets=[self.docs_dir / "templates" / f"{date}_gallery.md"],
                file_dep=self.db.get_all_assets(),
                task_dep=[f"create_directory:{self.templates_dir}"],
                uptodate=[True],
            )