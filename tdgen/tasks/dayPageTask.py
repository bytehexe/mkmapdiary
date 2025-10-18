from .base.baseTask import BaseTask
import datetime
import textwrap
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
                f.write(textwrap.dedent(f"""\
                # {formatted_date}

                --8<--
                docs/templates/{date}_gallery.md
                --8<--

                ## {self.config["map_title"]}

                ## {self.config["journal_title"]}
                
                """))
        
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
            with open(gallery_path, "w") as f:
                f.write(f"## { self.config['gallery_title'] }\n\n")
                f.write('<div class="grid cards" style="display: flex" markdown>\n')
                for asset in self.db.get_assets_by_date(date):
                    basename = pathlib.PosixPath(asset).name
                    f.write(f"- ![](assets/{basename}){{ style=\"position: absolute; left: 0; right: 0; top: 0; bottom: 0; margin: auto; max-width: 198px; max-height:198px\" }}\n")
                    f.write('  { style="width:200px; height:200px; position: relative;" }')
                    f.write('\n')
                f.write('</div>')

        for date in self.db.get_all_dates():
            yield dict(
                name=str(date),
                actions=[(_generate_gallery, [date])],
                targets=[self.docs_dir / "templates" / f"{date}_gallery.md"],
                file_dep=self.db.get_all_assets(),
                task_dep=[f"create_directory:{self.templates_dir}"],
                uptodate=[True],
            )