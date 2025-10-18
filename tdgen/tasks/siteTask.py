from .base.baseTask import BaseTask
import yaml

class SiteTask(BaseTask):
    def __init__(self):
        super().__init__()
    
    @property
    def __site_dirs(self):
        return [
            self.build_dir,
            self.assets_dir,
            self.docs_dir,
            self.dist_dir,
            self.files_dir,
        ]

    def task_create_directory(self):
        """Create a directory if it doesn't exist."""

        def _create_directory(dir):
            dir.mkdir(parents=True, exist_ok=True)

        for dir in self.__site_dirs:
            yield dict(
                    name=dir,
                    actions=[(_create_directory, (dir,))],
                    targets=[dir],
                    uptodate=[True],  # Always consider this task up-to-date after the first run
                )
            
    def task_generate_mkdocs_config(self):
        """Generate mkdocs config."""

        def _generate_mkdocs_config():

            config = {
                "site_name": self.config.get("site_name", "Travel Diary"),
                "docs_dir": str(self.docs_dir.absolute()),
                "site_dir": str(self.dist_dir.absolute()),
                "use_directory_urls": False,
                "theme": {
                    "name": self.config.get("theme", "material"),
                },
            }

            with open(self.build_dir / "mkdocs.yml", "w") as f:
                yaml.dump(config, f, sort_keys=False)

        return dict(
            actions=[(_generate_mkdocs_config, ())],
            targets=[self.build_dir / "mkdocs.yml"],
            task_dep=[f"create_directory:{self.build_dir}"],
            uptodate=[True],
        )
    
    def task_build_static_pages(self):
        yield dict(
            name="index",
            actions=[f"touch {self.docs_dir / 'index.md'}"],
            file_dep=[],
            task_dep=[
                f"create_directory:{self.dist_dir}",
            ],
            targets=[self.docs_dir / "index.md"],
            uptodate=[True],
        )

    def task_build_site(self):
        """Build the mkdocs site."""

        def _generate_file_deps():
            yield self.build_dir / "mkdocs.yml"
            yield self.docs_dir / "index.md"
            yield from self.db.get_all_assets()

        return dict(
            actions=["mkdocs build --clean --config-file " + str(self.build_dir / "mkdocs.yml")],
            file_dep=list(_generate_file_deps()),
            task_dep=[
                f"create_directory:{self.dist_dir}",
                "build_static_pages:*"
                "generate_mkdocs_config",
            ],
            targets=[
                self.dist_dir / "sitemap.xml",
            ],
            verbosity=2,
        )