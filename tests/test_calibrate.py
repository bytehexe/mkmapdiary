import calendar
import datetime

import whenever

from mkmapdiary.lib.calibration import Calibration
from mkmapdiary.tasks.base.baseTask import BaseTask


def test_pre_calibrate() -> None:
    dt1 = datetime.datetime(2023, 1, 1, 12, 0, 0)
    assert dt1.isoformat() == "2023-01-01T12:00:00"
    calibration = Calibration(timezone="UTC", offset=0)

    dt = whenever.PlainDateTime.from_py_datetime(dt1)

    assert dt.format_iso() == "2023-01-01T12:00:00"

    d_tz = dt.assume_tz(calibration.timezone)
    assert d_tz.format_iso() == "2023-01-01T12:00:00+00:00[UTC]"

    d_i = d_tz.to_instant()
    assert d_i.format_iso() == "2023-01-01T12:00:00Z"

    d_s = d_i.subtract(seconds=calibration.offset)
    assert d_s.format_iso() == "2023-01-01T12:00:00Z"

    assert d_tz.timestamp() == calendar.timegm(dt1.timetuple())


def test_calibrate_utc() -> None:
    dt = datetime.datetime(2023, 1, 1, 12, 0, 0)
    instant = BaseTask._calibrate(dt, Calibration(timezone="UTC", offset=0))

    assert instant.timestamp() == calendar.timegm(dt.timetuple())


def test_calibrate_offset() -> None:
    dt = datetime.datetime(2023, 1, 1, 12, 0, 0)
    offset_seconds = 60 * 5  # 5 minutes
    instant = BaseTask._calibrate(
        dt, Calibration(timezone="UTC", offset=offset_seconds)
    )

    assert instant.timestamp() == calendar.timegm(dt.timetuple()) - offset_seconds


def test_calibrate_timezone() -> None:
    dt = datetime.datetime(2023, 1, 1, 12, 0, 0)
    instant = BaseTask._calibrate(
        dt, Calibration(timezone="America/New_York", offset=0)
    )

    # New York is UTC-5 in January
    expected_timestamp = calendar.timegm(dt.timetuple()) + (5 * 60 * 60)
    assert instant.timestamp() == expected_timestamp
