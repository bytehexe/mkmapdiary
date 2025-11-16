from collections.abc import Callable
from pathlib import PosixPath
from typing import Any

from mkmapdiary.lib.calibration import Calibration
from mkmapdiary.tasks.base.baseTask import BaseTask


class MultiFormat(BaseTask):
    """A base class for tasks that support multiple output formats."""

    def setup_multiformat(self, key: str, callback: Callable) -> None:
        """Initialize the MultiFormat task with supported formats."""
        super().__init__()

        for format_string, option in self.config["input_formats"][key][
            "formats"
        ].items():
            if format_string.startswith("."):
                self.__register_extension_handler(format_string[1:], option, callback)
            else:
                self.__register_format_handler(format_string, option, callback)

    def __inject_option(self, option: str | None, callback: Callable) -> Callable:
        def wrapper(source: PosixPath, calibration: Calibration) -> list[Any]:
            if option is None:
                return []
            return callback(source, calibration, option)

        return wrapper

    def __register_extension_handler(
        self, ext: str, option: str | None, callback: Callable
    ) -> None:
        handler_name = f"handle_ext_{ext.lower()}"
        setattr(self, handler_name, self.__inject_option(option, callback))

    def __register_format_handler(
        self, format_name: str, option: str | None, callback: Callable
    ) -> None:
        handler_name = f"handle_{format_name.lower()}"
        setattr(self, handler_name, self.__inject_option(option, callback))
