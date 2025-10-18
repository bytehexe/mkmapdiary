import rawpy
import imageio.v2 as imageio

class Cr2Task:
    def __init__(self):
        super().__init__()
        self.__sources = []

    def __generate_intermediate_filename(self, source):
        return (self.build_dir / source.stem).with_suffix(".jpeg")

    def handle_ext_cr2(self, source):
        self.__sources.append(source)
        intermediate_file = self.__generate_intermediate_filename(source)
        self.handle_image(intermediate_file)

    def task_convert_raw(self):
        """Convert a RAW image to JPEG."""
        def _convert(src, dst):
            with rawpy.imread(str(src)) as raw:
                rgb = raw.postprocess(
                    use_camera_wb=True,      # Kamera-Weißabgleich
                    no_auto_bright=True,     # keine automatische Helligkeit
                    output_bps=8             # 8-bit pro Kanal (statt 16)
            )
            imageio.imwrite(dst, rgb)

        for src in self.__sources:
            dst = self.__generate_intermediate_filename(src)
            yield dict(
                    name=dst,
                    actions=[(_convert, (src, dst))],
                    file_dep=[src],
                    targets=[dst],
                    task_dep=[f"create_directory:{dst.parent}"],
                )