from PIL import Image

class ImageTask:
    def __init__(self):
        super().__init__()
        self.__sources = []

    def handle_image(self, source):
        # Create task to convert image to target format
        self.__sources.append(source)

    def task_convert_image(self):
        """Convert an image to a different format."""

        format = self.config.get("image_format", "jpg")

        def _convert(src, dst):
            with Image.open(src) as img:
                img.convert("RGB").save(dst)

        for src in self.__sources:
            dst = (self.assets_dir / src.stem).with_suffix(f".{format}")
            yield dict(
                    name=dst,
                    actions=[(_convert, (src, dst))],
                    file_dep=[src],
                    task_dep=[f"create_directory:{dst.parent}"],
                    targets=[dst],
                )