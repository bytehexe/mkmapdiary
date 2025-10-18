from .base.baseTask import BaseTask
import datetime
import textwrap

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
                
                ## {self.config["gallery_title"]}

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