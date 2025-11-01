from typing import NamedTuple


class Calibration(NamedTuple):
    timezone: str
    offset: int
