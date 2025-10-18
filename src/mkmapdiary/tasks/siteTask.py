from .base.baseTask import BaseTask
from .base.httpRequest import HttpRequest
import yaml
import pathlib
import datetime
import sass
import shutil
from typing import Callable, Dict, Iterator, List, Tuple, Union, Any


class SiteTask(HttpRequest):
    def __init__(self):
        super().__init__()

        self.__simple_assets = [
            "geo.js",
            "audio.js",
            "gallery.js",
            "cross-orange.svg",
            "logo-blue.svg",
            "logo-white.svg",
        ]

    @property
    def __site_dirs(self):
        return [
            self.build_dir,
            self.assets_dir,
            self.docs_dir,
            self.dist_dir,
            self.files_dir,
            self.templates_dir,
        ]

    def task_create_directory(self) -> Iterator[Dict[str, Any]]:
        """Create a directory if it doesn't exist."""

        def _create_directory(dir):
            dir.mkdir(parents=True, exist_ok=True)

        for dir in self.__site_dirs:
            yield dict(
                name=dir,
                actions=[(_create_directory, (dir,))],
                targets=[dir],
                uptodate=[
                    True
                ],  # Always consider this task up-to-date after the first run
            )

    def task_generate_mkdocs_config(self) -> Dict[str, Any]:
        """Generate mkdocs config."""

        def _generate_mkdocs_config():

            script_dir = pathlib.Path(__file__).parent
            with open(script_dir.parent / "extras" / "site_config.yaml") as f:
                config = yaml.safe_load(f)

            config["site_name"] = self.config["site_name"]
            config["docs_dir"] = str(self.docs_dir.absolute())
            config["site_dir"] = str(self.dist_dir.absolute())
            config["theme"]["language"] = self.config["locale"].split("_")[0]
            config["markdown_extensions"][0]["pymdownx.snippets"]["base_path"] = [
                self.build_dir
            ]

            with open(self.build_dir / "mkdocs.yml", "w") as f:
                yaml.dump(config, f, sort_keys=False)

        return dict(
            actions=[(_generate_mkdocs_config, ())],
            targets=[self.build_dir / "mkdocs.yml"],
            task_dep=[f"create_directory:{self.build_dir}"],
            uptodate=[True],
        )

    def task_build_static_pages(self) -> Iterator[Dict[str, Any]]:
        def _generate_index_page():
            index_path = self.docs_dir / "index.md"

            images = [
                pathlib.PosixPath(x[0]) for x in self.db.get_assets_by_type("image")
            ]

            with open(index_path, "w") as f:
                f.write(
                    self.template(
                        "index.j2",
                        home_title=self.config["home_title"],
                        gallery_title=self.config["gallery_title"],
                        grid_items=images,
                    )
                )

        yield dict(
            name="index",
            actions=[_generate_index_page],
            file_dep=self.db.get_all_assets(),
            calc_dep=["get_gpx_deps"],
            task_dep=[
                f"create_directory:{self.dist_dir}",
            ],
            targets=[self.docs_dir / "index.md"],
            uptodate=[True],
        )

    def task_compile_css(self) -> Dict[str, Any]:
        script_dir = pathlib.Path(__file__).parent
        input_sass = script_dir.parent / "extras" / "extra.sass"
        output_css = self.docs_dir / "extra.css"

        def _http_importer(path):
            try:
                prefix, name = path.split(":", 1)
            except ValueError:
                return None  # Not a special import, use default behavior

            if prefix != "source":
                return None  # Not a special import, use default behavior

            sources = {
                "material-color.scss": "https://unpkg.com/material-design-color@2.3.2/material-color.scss"
            }

            try:
                url = sources[name]
            except KeyError:
                raise ImportError(f"Unknown import source: {name}")

            response = self.httpRequest(url, data={}, headers={}, json=False)

            return [(name, response)]

        def _generate():
            css = sass.compile(
                filename=str(input_sass),
                output_style="compressed",
                importers=[(0, _http_importer)],
            )
            with open(str(output_css), "w") as f:
                f.write(css)

        return dict(actions=[_generate], file_dep=[input_sass], targets=[output_css])

    def task_copy_simple_asset(self) -> Iterator[Dict[str, Any]]:
        simple_assets = self.__simple_assets

        script_dir = pathlib.Path(__file__).parent

        def _generate(input_js, output_js):
            shutil.copy2(input_js, output_js)

        for asset in simple_assets:
            input = script_dir.parent / "extras" / asset
            output = self.docs_dir / asset

            yield dict(
                name=asset,
                actions=[(_generate, (input, output))],
                file_dep=[input],
                targets=[output],
            )

    def task_build_site(self) -> Dict[str, Any]:
        """Build the mkdocs site."""

        def _generate_file_deps():
            yield self.build_dir / "mkdocs.yml"
            yield self.docs_dir / "index.md"
            yield from self.db.get_all_assets()
            for date in self.db.get_all_dates():
                yield self.docs_dir / f"{date}.md"
                yield self.templates_dir / f"{date}_gallery.md"
                yield self.templates_dir / f"{date}_journal.md"
                yield self.templates_dir / f"{date}_tags.md"
            for asset in self.__simple_assets:
                yield self.docs_dir / asset

        return dict(
            actions=[
                "mkdocs build --clean --config-file "
                + str(self.build_dir / "mkdocs.yml")
            ],
            file_dep=list(_generate_file_deps()),
            task_dep=[
                f"create_directory:{self.dist_dir}",
                "build_static_pages",
                "generate_mkdocs_config",
                "compile_css",
                "build_day_page",
                "build_gallery",
                "build_journal",
                "build_tags",
            ],
            calc_dep=["get_gpx_deps"],
            targets=[
                self.dist_dir / "sitemap.xml",
            ],
            verbosity=2,
        )
