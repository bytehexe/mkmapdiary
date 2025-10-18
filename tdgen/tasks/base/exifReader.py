import exiftool
import datetime


class ExifReader:
    def read_exif(self, source):

        meta = {}

        # Try to extract time from exif data
        with exiftool.ExifToolHelper() as et:
            try:
                exif_data = et.get_metadata([source])[0]
            except exiftool.exceptions.ExifToolExecuteError:
                meta["date"] = self.extract_meta_datetime(source)
                return meta

        if not exif_data:
            meta["date"] = self.extract_meta_datetime(source)
            return meta

        try:
            create_date = exif_data["EXIF:CreateDate"]
            meta["date"] = datetime.datetime.strptime(create_date, "%Y:%m:%d %H:%M:%S")
        except KeyError:
            meta["date"] = self.extract_meta_datetime(source)

        try:
            meta["latitude"] = exif_data["Composite:GPSLatitude"]
            meta["longitude"] = exif_data["Composite:GPSLongitude"]
        except KeyError:
            pass

        return meta
