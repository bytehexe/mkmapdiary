#!/usr/bin/env python3
import pathlib
import subprocess
import sys

if not pathlib.PosixPath("demo").is_dir():
    p = subprocess.run(["mkmapdiary", "generate-demo", "demo"] + sys.argv[1:])
    sys.exit(p.returncode)

p = subprocess.run(["mkmapdiary", "build", "-Ba", "demo"] + sys.argv[1:])
sys.exit(p.returncode)
