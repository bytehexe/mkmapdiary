from .base.baseTask import BaseTask
from pathlib import PosixPath
from typing import Any, Dict, Iterator, List, Union


class QstarzTask(BaseTask):
    def __init__(self):
        super().__init__()
        self.__sources = []

    def handle_ext_bin(self, source: PosixPath) -> List[Any]:
        return self.__handle(source)

    def handle_ext_poi(self, source: PosixPath) -> List[Any]:
        return self.__handle(source)

    def handle_ext_dat(self, source: PosixPath) -> List[Any]:
        # Ignore .dat files, as they are not directly supported by gpsbabel
        return []

    def __handle(self, source):
        self.__sources.append(source)
        intermediate_file = self.__generate_destination_filename(source)

        assets = list(self.handle_gpx(intermediate_file))
        return assets

    def __generate_destination_filename(self, source):
        filename = (self.files_dir / source.stem).with_suffix(
            f"{source.suffix[0:2]}.gpx"
        )
        return self.make_unique_filename(source, filename)

    def task_qstarz2gpx(self) -> Iterator[Dict[str, Any]]:
        for source in self.__sources:
            dst = self.__generate_destination_filename(source)
            yield {
                "name": f"{source}",
                "file_dep": [source],
                "targets": [dst],
                "actions": [
                    "gpsbabel -t -w -r -i qstarz_bl-1000 -f %(dependencies)s -o gpx -F %(targets)s"
                ],
                "clean": True,
            }
