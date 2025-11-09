import logging
import pathlib
import random
import shutil
from collections.abc import Iterator
from typing import Any

import sass
import yaml
from doit import create_after

from mkmapdiary.lib.startPage import StartPage

from .base.httpRequest import HttpRequest

logger = logging.getLogger(__name__)


class SiteTask(HttpRequest):
    def __init__(self) -> None:
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
    def __site_dirs(self) -> list[pathlib.Path]:
        return [
            self.dirs.build_dir,
            self.dirs.assets_dir,
            self.dirs.docs_dir,
            self.dirs.dist_dir,
            self.dirs.files_dir,
            self.dirs.templates_dir,
        ]

    def task_create_directory(self) -> Iterator[dict[str, Any]]:
        """Create a directory if it doesn't exist."""

        def _create_directory(dir_name: pathlib.Path) -> None:
            dir_name.mkdir(parents=True, exist_ok=True)

        for dir_name in self.__site_dirs:
            yield dict(
                name=dir_name,
                actions=[(_create_directory, (dir_name,))],
                targets=[dir_name],
                uptodate=[
                    False,
                ],  # Always consider this task up-to-date after the first run
            )

    def task_generate_mkdocs_config(self) -> dict[str, Any]:
        """Generate mkdocs config."""

        def _generate_mkdocs_config() -> None:
            script_dir = pathlib.Path(__file__).parent
            with open(script_dir.parent / "resources" / "site_config.yaml") as f:
                config = yaml.safe_load(f)

            config["site_name"] = self.config["strings"]["site_name"]

            # compute paths relative to mkdocs.yml location
            try:
                config["docs_dir"] = str(
                    self.dirs.docs_dir.relative_to(self.dirs.build_dir),
                )
                config["site_dir"] = str(
                    self.dirs.dist_dir.relative_to(self.dirs.build_dir, walk_up=True),
                )
            except ValueError:
                config["docs_dir"] = str(self.dirs.docs_dir.absolute())
                config["site_dir"] = str(self.dirs.dist_dir.absolute())

            language = self.config["site"]["locale"].split("_")[0]
            config["theme"]["language"] = language
            config["markdown_extensions"][0]["pymdownx.snippets"]["base_path"] = [
                self.dirs.build_dir,
            ]

            with open(self.dirs.build_dir / "mkdocs.yml", "w") as f:
                yaml.dump(config, f, sort_keys=False)

        return dict(
            actions=[(_generate_mkdocs_config, ())],
            targets=[self.dirs.build_dir / "mkdocs.yml"],
            task_dep=[f"create_directory:{self.dirs.build_dir}"],
            uptodate=[False],
        )

    @create_after("end_postprocessing")
    def task_build_index_page(self) -> dict[str, Any]:
        def _generate_index_page() -> None:
            index_path = self.dirs.docs_dir / "index.md"

            images = self.db.get_assets_by_type("image")

            logger.info("Generating index page data ...")
            page_info = StartPage(images, self.config)
            logger.info("Generating index page ...")
            logger.debug(f"Gallery assets: {len(page_info.gallery_assets)}")
            logger.debug(f"Map assets: {len(page_info.map_assets)}")
            logger.debug(f"With map: {page_info.with_map}")
            logger.debug(f"Gallery rows: {page_info.gallery_rows}")

            # Randomize gallery assets
            random.shuffle(page_info.gallery_assets)

            geo_assets = []
            for i, geo_asset in enumerate(page_info.map_assets):
                geo_item = dict(
                    photo="assets/" + str(geo_asset.path).split("/")[-1],
                    thumbnail="assets/" + str(geo_asset.path).split("/")[-1],
                    lat=geo_asset.latitude,
                    lng=geo_asset.longitude,
                    index=i + len(page_info.gallery_assets),
                )
                geo_assets.append(geo_item)

            with open(index_path, "w") as f:
                f.write(
                    self.template(
                        "index.j2",
                        home_title=self.config["strings"]["home_title"],
                        gallery_title=self.config["strings"]["gallery_title"],
                        map_title=self.config["strings"]["map_title"],
                        gallery_images=page_info.gallery_assets + page_info.map_assets,
                        map_images=geo_assets,
                        with_map=page_info.with_map,
                        gallery_rows=page_info.gallery_rows,
                    ),
                )

        return dict(
            actions=[_generate_index_page],
            file_dep=[str(asset.path) for asset in self.db.get_all_assets()],
            calc_dep=["get_gpx_deps"],
            task_dep=[
                f"create_directory:{self.dirs.dist_dir}",
            ],
            targets=[self.dirs.docs_dir / "index.md"],
            uptodate=[False],
        )

    def task_compile_css(self) -> dict[str, Any]:
        input_sass = self.dirs.resources_dir / "extra.sass"
        output_css = self.dirs.docs_dir / "extra.css"

        def _http_importer(path: str) -> list[tuple[str, str]] | None:
            try:
                prefix, name = path.split(":", 1)
            except ValueError:
                return None  # Not a special import, use default behavior

            if prefix != "source":
                return None  # Not a special import, use default behavior

            sources = {
                "material-color.scss": "https://unpkg.com/material-design-color@2.3.2/material-color.scss",
            }

            try:
                url = sources[name]
            except KeyError as e:
                raise ImportError(f"Unknown import source: {name}") from e

            response = self.httpRequest(url, data={}, headers={}, json=False)

            # Ensure response is a string since json=False
            assert isinstance(response, str), (
                "Response should be a string when json=False"
            )
            return [(name, response)]

        def _generate() -> None:
            css = sass.compile(
                filename=str(input_sass),
                output_style="compressed",
                importers=[(0, _http_importer)],
            )
            with open(str(output_css), "w") as f:
                f.write(css)

        return dict(actions=[_generate], file_dep=[input_sass], targets=[output_css])

    def task_copy_simple_asset(self) -> Iterator[dict[str, Any]]:
        simple_assets = self.__simple_assets

        def _generate(input_js: pathlib.Path, output_js: pathlib.Path) -> None:
            shutil.copy2(input_js, output_js)

        for asset in simple_assets:
            input_file = self.dirs.resources_dir / asset
            output = self.dirs.docs_dir / asset

            yield dict(
                name=asset,
                actions=[(_generate, (input_file, output))],
                file_dep=[input_file],
                targets=[output],
            )

    def task_pre_build_site(self) -> dict[str, Any]:
        # Ensure that the site directories exist
        return {
            "actions": None,
            "task_dep": [
                f"create_directory:{self.dirs.build_dir}",
                f"create_directory:{self.dirs.assets_dir}",
                f"create_directory:{self.dirs.docs_dir}",
                f"create_directory:{self.dirs.dist_dir}",
                f"create_directory:{self.dirs.files_dir}",
                f"create_directory:{self.dirs.templates_dir}",
                "geo_correlation",
            ],
        }

    @create_after("end_postprocessing")
    def task_build_site(self) -> dict[str, Any]:
        """Build the mkdocs site."""

        def _generate_file_deps() -> Iterator[Any]:
            yield self.dirs.build_dir / "mkdocs.yml"
            yield self.dirs.docs_dir / "index.md"
            yield from (str(asset.path) for asset in self.db.get_all_assets())
            for date in self.db.get_all_dates():
                yield self.dirs.docs_dir / f"{date}.md"
                yield self.dirs.templates_dir / f"{date}_gallery.md"
                yield self.dirs.templates_dir / f"{date}_journal.md"
                yield self.dirs.templates_dir / f"{date}_tags.md"
            for asset in self.__simple_assets:
                yield self.dirs.docs_dir / asset

        return dict(
            actions=[
                "mkdocs build --clean --config-file "
                + str(self.dirs.build_dir / "mkdocs.yml"),
            ],
            file_dep=list(_generate_file_deps()),
            task_dep=[
                f"create_directory:{self.dirs.dist_dir}",
                "build_index_page",
                "generate_mkdocs_config",
                "compile_css",
                "build_day_page",
                "build_gallery",
                "build_journal",
                "build_tags",
                "geo_correlation",
                "pre_build_site",
            ],
            calc_dep=["get_gpx_deps"],
            targets=[
                self.dirs.dist_dir / "sitemap.xml",
            ],
        )
