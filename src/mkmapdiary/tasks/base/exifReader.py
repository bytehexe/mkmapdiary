import dataclasses
import datetime
import logging
from abc import ABC, abstractmethod
from pathlib import PosixPath

import exiftool
import whenever

from mkmapdiary.lib.calibration import Calibration

logger = logging.getLogger(__name__)


@dataclasses.dataclass
class ExifData:
    create_date: whenever.Instant | None = None
    latitude: float | None = None
    longitude: float | None = None
    orientation: int | None = None


class ExifReader(ABC):
    @abstractmethod
    def extract_meta_datetime(
        self, source: PosixPath, calibration: Calibration
    ) -> whenever.Instant | None:
        raise NotImplementedError

    @abstractmethod
    def calibrate(
        self, dt: whenever.PlainDateTime | datetime.datetime, calibration: Calibration
    ) -> whenever.Instant:
        pass

    def read_exif(self, source: PosixPath, calibration: Calibration) -> ExifData:
        exif_data: ExifData = ExifData()
        exif_data_dict = {}

        # Try to extract time from exif data
        with exiftool.ExifToolHelper() as et:
            try:
                exif_data_dict = et.get_metadata([source])[0]
            except exiftool.exceptions.ExifToolExecuteError as e:
                exif_data.create_date = self.extract_meta_datetime(source, calibration)
                logger.debug(f"Failed to read EXIF data from {source} ({e})")
                return exif_data

        if not exif_data_dict:
            exif_data.create_date = self.extract_meta_datetime(source, calibration)
            logger.debug(f"Failed to read EXIF data from {source} (no data)")
            return exif_data

        date_formats = [
            # strptime format, exif tag, is UTC
            ("%Y:%m:%d %H:%M:%S.%f", "Composite:SubSecDateTimeOriginal", False),
            ("%Y:%m:%d %H:%M:%S", "EXIF:DateTimeOriginal", False),
            ("%Y:%m:%d %H:%M:%S.%f", "Composite:SubSecCreateDate", False),
            ("%Y:%m:%d %H:%M:%S", "EXIF:CreateDate", False),
        ]

        for date_format, tag, is_true_utc in date_formats:
            try:
                create_date = exif_data_dict[tag]
                py_datetime = datetime.datetime.strptime(
                    create_date,
                    date_format,
                )
            except (KeyError, ValueError):
                logger.debug(
                    f"EXIF tag {tag} not found or invalid in {source}, trying next."
                )
                continue
            else:
                logger.debug(
                    f"Found EXIF CreateDate {create_date} in tag {tag} for {source}"
                )
                if is_true_utc:
                    exif_data.create_date = self.calibrate(
                        py_datetime, Calibration("UTC", 0)
                    )
                else:
                    exif_data.create_date = self.calibrate(py_datetime, calibration)
                break

        if exif_data.create_date is None:
            logger.debug(
                f"Failed to read EXIF CreateDate from {source}, falling back to file datetime."
            )
            exif_data.create_date = self.extract_meta_datetime(source, calibration)

        try:
            exif_data.latitude = exif_data_dict["Composite:GPSLatitude"]
            exif_data.longitude = exif_data_dict["Composite:GPSLongitude"]
        except KeyError:
            pass

        try:
            exif_data.orientation = exif_data_dict.get("EXIF:Orientation", 1)
        except KeyError:
            pass

        logger.debug(f"EXIF data for {source}: {exif_data}")
        return exif_data
