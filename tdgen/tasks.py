import shutil
from doit.task import Task
import rawpy
import imageio.v2 as imageio

def copy_file(src, dst):
    """Copy a file from src to dst."""
    return Task(
            name=f"copy_file:{dst}",
            actions=[(shutil.copy2, (src, dst))],
            file_dep=[src],
            task_dep=[f"create_directory:{dst.parent}"],
            targets=[dst],
        )
    
def convert_image(src, dst, format="jpeg"):
    """Convert an image to a different format."""
    from PIL import Image
    def _convert():
        with Image.open(src) as img:
            img.convert("RGB").save(dst, format=format)

    return Task(
            name=f"convert_image:{dst}",
            actions=[_convert],
            file_dep=[src],
            task_dep=[f"create_directory:{dst.parent}"],
            targets=[dst],
        )

def convert_raw(src, dst):
    """Convert a RAW image to JPEG."""
    def _convert():
        with rawpy.imread(str(src)) as raw:
            rgb = raw.postprocess(
                use_camera_wb=True,      # Kamera-Weißabgleich
                no_auto_bright=True,     # keine automatische Helligkeit
                output_bps=8             # 8-bit pro Kanal (statt 16)
        )
        imageio.imwrite(dst, rgb)

    return Task(
            name=f"convert_raw:{dst}",
            actions=[_convert],
            file_dep=[src],
            targets=[dst],
            task_dep=[f"create_directory:{dst.parent}"],
        )

def create_directory(path):
    """Create a directory if it doesn't exist."""
    return Task(
            name=f"create_directory:{path}",
            actions=[(shutil.os.makedirs, (path,), {'exist_ok': True})],
            targets=[path],
        )