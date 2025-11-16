from abc import abstractmethod
from collections.abc import Iterator
from pathlib import PosixPath
from typing import Any

from mkmapdiary.lib.calibration import Calibration
from mkmapdiary.tasks.base.multiFormat import MultiFormat


class GpsbabelInputTask(MultiFormat):
    @abstractmethod
    def handle_gpx(self, source: PosixPath, calibration: Calibration) -> list[Any]:
        pass

    def __init__(self) -> None:
        super().__init__()
        self.setup_multiformat("gpsbabel", self.__handle)
        self.__sources: list[PosixPath] = []
        self.__options: dict[PosixPath, str] = {}

    def __handle(
        self, source: PosixPath, calibration: Calibration, option: str
    ) -> list[Any]:
        self.__sources.append(source)
        self.__options[source] = option
        intermediate_file = self._generate_destination_filename(source)

        assets = list(self.handle_gpx(intermediate_file, calibration))
        return assets

    def _generate_destination_filename(self, source: PosixPath) -> PosixPath:
        filename = PosixPath(self.dirs.files_dir / source.stem).with_suffix(
            f"{source.suffix[0:2]}.gpx",
        )
        return self.make_unique_filename(source, filename)

    def task_qstarz2gpx(self) -> Iterator[dict[str, Any]]:
        for source in self.__sources:
            dst = self._generate_destination_filename(source)
            option = self.__options[source]
            yield {
                "name": f"{source}",
                "file_dep": [source],
                "task_dep": [f"create_directory:{self.dirs.files_dir}"],
                "targets": [dst],
                "actions": [
                    f"gpsbabel -t -w -r -i {option} -f %(dependencies)s -o gpx -F %(targets)s",
                ],
                "clean": True,
            }
