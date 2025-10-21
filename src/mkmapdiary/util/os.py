import pathlib
import shutil


def clean_dir(build_dir: pathlib.Path):
    for item in build_dir.iterdir():
        if item.is_dir():
            shutil.rmtree(item)
        else:
            item.unlink()
