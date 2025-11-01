#! /usr/bin/env python3

import hashlib
import pathlib
import subprocess
import sys
import tempfile

import click


def compute_sha1_checksum(file_path):
    sha1 = hashlib.sha1()
    with open(file_path, "rb") as f:
        while True:
            data = f.read(65536)  # Read in 64KB chunks
            if not data:
                break
            sha1.update(data)
    return sha1.hexdigest()


@click.command()
@click.option(
    "--check",
    is_flag=True,
    help="Check if translation files are up to date.",
)
def cli(check) -> None:
    locale_dir = pathlib.Path(".") / "src" / "mkmapdiary" / "locale"

    languages = [
        d.name
        for d in locale_dir.iterdir()
        if d.is_dir() and (d / "LC_MESSAGES").is_dir()
    ]

    outdated_languages = set()

    for lang in languages:
        po_file = locale_dir / lang / "LC_MESSAGES" / "messages.po"
        mo_file = locale_dir / lang / "LC_MESSAGES" / "messages.mo"

        try:
            mo_checksum = compute_sha1_checksum(mo_file)
        except FileNotFoundError:
            mo_checksum = None

        if check:
            with tempfile.NamedTemporaryFile(delete=False) as temp_mo:
                subprocess.run(
                    ["msgfmt", "-o", temp_mo.name, str(po_file)],
                    check=True,
                )
                new_mo_checksum = compute_sha1_checksum(temp_mo.name)

                if new_mo_checksum != mo_checksum:
                    outdated_languages.add(lang)
        else:
            subprocess.run(
                ["msgfmt", "-o", str(mo_file), str(po_file)],
                check=True,
            )
            new_mo_checksum = compute_sha1_checksum(mo_file)
            if new_mo_checksum != mo_checksum:
                print(f"Updated translation for language: {lang}")

    if check:
        if outdated_languages:
            print("The following languages have outdated translation files:")
            for lang in outdated_languages:
                print(f"- {lang}")
            sys.exit(1)
        else:
            print("All translation files are up to date.")
            sys.exit(0)


if __name__ == "__main__":
    cli()
