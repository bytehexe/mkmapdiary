from PIL import Image
from .baseTask import BaseTask
import exif
import datetime

class ImageTask(BaseTask):
    def __init__(self):
        super().__init__()
        self.__sources = []

    def handle_image(self, source):
        # Create task to convert image to target format
        self.__sources.append(source)

        # Try to extract time from exif data
        exif_data = exif.Image(source)

        meta = {}
        if exif_data.has_exif and hasattr(exif_data, "datetime_original"):
            meta["date"] = datetime.datetime.strptime(exif_data.datetime_original, "%Y:%m:%d %H:%M:%S")
        else:
            meta["date"] = self.extract_meta_mtime(source)

        return self.Asset(
            self.__generate_destination_filename(source),
            "image",
            meta
        )
    
    def __generate_destination_filename(self, source):
        format = self.config.get("image_format", "jpg")
        return (self.assets_dir / source.stem).with_suffix(f".{format}")

    def task_convert_image(self):
        """Convert an image to a different format."""

        
        def _convert(src, dst):
            with Image.open(src) as img:
                img.convert("RGB").save(dst)

        for src in self.__sources:
            dst = self.__generate_destination_filename(src)
            yield dict(
                    name=dst,
                    actions=[(_convert, (src, dst))],
                    file_dep=[src],
                    task_dep=[f"create_directory:{dst.parent}"],
                    targets=[dst],
                )