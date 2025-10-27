import pathlib

from platformdirs import PlatformDirs


class Dirs:
    def __init__(
        self,
        source_dir: pathlib.Path,
        build_dir: pathlib.Path,
        dist_dir: pathlib.Path,
        create_dirs: bool = True,
    ):
        self.__source_dir = source_dir

        self.__build_dir = build_dir
        self.__dist_dir = dist_dir
        self.__sys_dirs = PlatformDirs("mkmapdiary", "bytehexe")
        self.create_dirs = create_dirs

    @property
    def source_dir(self) -> pathlib.Path:
        return self.__source_dir

    @property
    def build_dir(self) -> pathlib.Path:
        build_path = self.__build_dir
        if self.create_dirs:
            build_path.mkdir(parents=True, exist_ok=True)
        return build_path

    @property
    def dist_dir(self) -> pathlib.Path:
        return self.__dist_dir

    @property
    def files_dir(self) -> pathlib.Path:
        files_path = self.build_dir / "files"
        if self.create_dirs:
            files_path.mkdir(parents=True, exist_ok=True)
        return files_path

    @property
    def docs_dir(self) -> pathlib.Path:
        docs_path = self.build_dir / "docs"
        if self.create_dirs:
            docs_path.mkdir(parents=True, exist_ok=True)
        return docs_path

    @property
    def templates_dir(self) -> pathlib.Path:
        templates_path = self.docs_dir / "templates"
        if self.create_dirs:
            templates_path.mkdir(parents=True, exist_ok=True)
        return templates_path

    @property
    def assets_dir(self) -> pathlib.Path:
        assets_path = self.docs_dir / "assets"
        if self.create_dirs:
            assets_path.mkdir(parents=True, exist_ok=True)
        return assets_path

    @property
    def user_cache_dir(self) -> pathlib.Path:
        cache_path = pathlib.Path(self.__sys_dirs.user_cache_dir)
        if self.create_dirs:
            cache_path.mkdir(parents=True, exist_ok=True)
        return cache_path

    @property
    def user_config_dir(self) -> pathlib.Path:
        config_path = pathlib.Path(self.__sys_dirs.user_config_dir)
        if self.create_dirs:
            config_path.mkdir(parents=True, exist_ok=True)
        return config_path

    @property
    def user_data_dir(self) -> pathlib.Path:
        data_path = pathlib.Path(self.__sys_dirs.user_data_dir)
        if self.create_dirs:
            data_path.mkdir(parents=True, exist_ok=True)
        return data_path

    @property
    def cache_db_path(self) -> pathlib.Path:
        db_path = self.user_cache_dir / "db.sqlite"
        return db_path

    @property
    def region_cache_dir(self) -> pathlib.Path:
        region_path = self.user_cache_dir / "regions"
        if self.create_dirs:
            region_path.mkdir(parents=True, exist_ok=True)
        return region_path

    def get_region_cache(self, region_name: str) -> pathlib.Path:
        region_path = self.region_cache_dir / region_name
        if self.create_dirs:
            region_path.mkdir(parents=True, exist_ok=True)
        return region_path

    @property
    def log_file_path(self) -> pathlib.Path:
        log_path = self.build_dir / "mkmapdiary.log"
        return log_path

    def get_script_dir(self, file: str) -> pathlib.Path:
        return pathlib.Path(file).parent

    @property
    def resources_dir(self) -> pathlib.Path:
        script_dir = self.get_script_dir(__file__)
        resources_path = script_dir.parent / "resources"
        return resources_path

    @property
    def locale_dir(self) -> pathlib.Path:
        script_dir = self.get_script_dir(__file__)
        locale_path = script_dir.parent / "locale"
        return locale_path

    @property
    def user_config_file(self) -> pathlib.Path:
        config_path = self.user_config_dir / "config.yaml"
        return config_path

    @property
    def doit_db_path(self) -> pathlib.Path:
        db_path = self.build_dir / "doit.db"
        return db_path

    @property
    def build_dir_marker_file(
        self,
    ) -> pathlib.Path:
        marker_path = self.build_dir / ".mkmapdiary_build_dir"
        return marker_path
