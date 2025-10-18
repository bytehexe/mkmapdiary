import exiftool
import datetime

class ExifReader:
    def read_exif(self, source):

        # Try to extract time from exif data
        with exiftool.ExifToolHelper() as et:
            exif_data = et.get_metadata([source])[0]
        meta = {}

        if not exif_data:
            meta["date"] = self.extract_meta_mtime(source)
            return meta
        
        try:
            meta["date"] = exif_data["EXIF:CreateDate"]
        except KeyError:
            meta["date"] = self.extract_meta_mtime(source)

        try:
            meta["latitude"] = exif_data["Composite:GPSLatitude"]
            meta["longitude"] = exif_data["Composite:GPSLongitude"]
        except KeyError:
            pass

        return meta