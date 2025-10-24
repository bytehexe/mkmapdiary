import pathlib
import shutil
from typing import Optional, List


def clean_dir(build_dir: pathlib.Path, keep_files: Optional[List[str]] = None):
    if keep_files is None:
        keep_files = []
    for item in build_dir.iterdir():
        if item.is_dir():
            shutil.rmtree(item)
        else:
            if item.name not in keep_files:
                item.unlink()
