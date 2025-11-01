import time
from pathlib import Path
from typing import Any, Union

import msgpack

from mkmapdiary.poi.common import get_hash


class IndexFileWriter:
    def __init__(self, file_path: Union[str, Path], filter_config: dict):
        self.file_path = file_path
        with open(self.file_path, "wb") as f:
            self.packer = msgpack.Packer()
            f.write(
                self.packer.pack(
                    {
                        "version": 1,
                        "filter_hash": get_hash(filter_config),
                        "build_time": time.time(),
                    },
                ),
            )

    def write(self, index: Any) -> None:
        with open(self.file_path, "ab") as f:
            f.write(self.packer.pack(index))


if __name__ == "__main__":
    writer = IndexFileWriter("test_index.idx", filter_config={})
    index_data = {
        "test_key": "test_value",
    }
    writer.write(index_data)
