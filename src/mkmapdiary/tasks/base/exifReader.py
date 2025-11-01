import dataclasses
import datetime
import logging
from abc import ABC, abstractmethod
from pathlib import PosixPath
from typing import Optional, Union

import exiftool
import whenever

logger = logging.getLogger(__name__)


@dataclasses.dataclass
class ExifData:
    create_date: Optional[whenever.Instant] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    orientation: Optional[int] = None


class ExifReader(ABC):
    @abstractmethod
    def extract_meta_datetime(self, source: PosixPath) -> Optional[whenever.Instant]:
        raise NotImplementedError

    @abstractmethod
    def calibrate(
        self, dt: Union[whenever.PlainDateTime, datetime.datetime]
    ) -> whenever.Instant:
        pass

    def read_exif(self, source: PosixPath) -> ExifData:
        exif_data: ExifData = ExifData()
        exif_data_dict = {}

        # Try to extract time from exif data
        with exiftool.ExifToolHelper() as et:
            try:
                exif_data_dict = et.get_metadata([source])[0]
            except exiftool.exceptions.ExifToolExecuteError as e:
                exif_data.create_date = self.extract_meta_datetime(source)
                logger.debug(f"Failed to read EXIF data from {source} ({e})")
                return exif_data

        if not exif_data_dict:
            exif_data.create_date = self.extract_meta_datetime(source)
            logger.debug(f"Failed to read EXIF data from {source} (no data)")
            return exif_data

        try:
            create_date = exif_data_dict["Composite:SubSecCreateDate"]
            py_datetime = datetime.datetime.strptime(
                create_date,
                "%Y:%m:%d %H:%M:%S.%f",
            )
            logger.debug(f"EXIF CreateDate for {source}: {create_date} {py_datetime}")
            exif_data.create_date = self.calibrate(py_datetime)
        except KeyError as e:
            exif_data.create_date = self.extract_meta_datetime(source)
            logger.debug(f"Failed to read EXIF CreateDate from {source} ({e})")

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
