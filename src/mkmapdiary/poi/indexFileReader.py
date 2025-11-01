import time

import msgpack

from mkmapdiary.poi.common import get_hash


class IndexFileReader:
    def __init__(self, file_path) -> None:
        self.file_path = file_path

        with open(self.file_path, "rb") as f:
            self.unpacker = msgpack.Unpacker(f, strict_map_key=False)
            self.__header = self.unpacker.unpack()

    @property
    def header(self):
        return self.__header

    def is_valid(self, filter_config: dict) -> bool:
        expected_hash = get_hash(filter_config)
        return self.header.get("filter_hash") == expected_hash

    def is_up_to_date(self, age_limit: float) -> bool:
        build_time = self.header.get("build_time", 0)
        current_time = time.time()
        return (current_time - build_time) <= age_limit

    def read(self):
        with open(self.file_path, "rb") as f:
            unpacker = msgpack.Unpacker(f, strict_map_key=False)
            unpacker.skip()  # Skip header
            return unpacker.unpack()


if __name__ == "__main__":
    reader = IndexFileReader("test_index.idx")
    index = reader.read()
    print(reader.header)
    print(index)
