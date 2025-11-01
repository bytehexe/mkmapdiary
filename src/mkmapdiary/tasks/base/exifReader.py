import dataclasses
import datetime
from abc import ABC, abstractmethod
from pathlib import PosixPath
from typing import Optional

import exiftool


@dataclasses.dataclass
class ExifData:
    create_date: Optional[datetime.datetime] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    orientation: Optional[int] = None


class ExifReader(ABC):
    @abstractmethod
    def extract_meta_datetime(self, source: PosixPath) -> Optional[datetime.datetime]:
        pass

    def read_exif(self, source: PosixPath) -> ExifData:
        exif_data: ExifData = ExifData()
        exif_data_dict = {}

        # Try to extract time from exif data
        with exiftool.ExifToolHelper() as et:
            try:
                exif_data_dict = et.get_metadata([source])[0]
            except exiftool.exceptions.ExifToolExecuteError:
                exif_data.create_date = self.extract_meta_datetime(source)
                return exif_data

        if not exif_data_dict:
            exif_data.create_date = self.extract_meta_datetime(source)
            return exif_data

        try:
            create_date = exif_data_dict["EXIF:CreateDate"]
            exif_data.create_date = datetime.datetime.strptime(
                create_date,
                "%Y:%m:%d %H:%M:%S",
            )
        except KeyError:
            exif_data.create_date = self.extract_meta_datetime(source)

        try:
            exif_data.latitude = exif_data_dict["Composite:GPSLatitude"]
            exif_data.longitude = exif_data_dict["Composite:GPSLongitude"]
        except KeyError:
            pass

        try:
            exif_data.orientation = exif_data_dict.get("EXIF:Orientation", 1)
        except KeyError:
            pass

        return exif_data
