#!/usr/bin/env python3
import pathlib
import subprocess

if not pathlib.PosixPath("demo").is_dir():
    subprocess.run("mkmapdiary -T demo", shell=True, check=True)

subprocess.run("mkmapdiary -Ba demo", shell=True, check=True)
