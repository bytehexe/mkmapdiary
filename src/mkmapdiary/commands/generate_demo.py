import datetime
import pathlib
import random
import subprocess
import sys

import click
import ollama
import requests


def generate_demo_data(demo_data_dir: pathlib.Path):
    if not demo_data_dir.exists():
        demo_data_dir.mkdir(parents=True, exist_ok=True)
    elif any(demo_data_dir.iterdir()):
        click.echo(
            f"Source directory '{demo_data_dir}' must be empty to generate demo data.",
        )
        sys.exit(1)

    click.echo(f"Generating demo data in '{demo_data_dir}' ...")

    click.echo("  Creating text files...")
    create_demo_text_files(demo_data_dir)
    click.echo("  Creating markdown files...")
    create_demo_markdown_files(demo_data_dir)
    click.echo("  Creating audio files...")
    create_demo_audio_files(demo_data_dir)
    click.echo("  Creating image files...")
    create_demo_image_files(demo_data_dir)
    click.echo("  Creating map files...")
    create_demo_map_files(demo_data_dir)
    click.echo("Demo data generation complete.")


def create_demo_text_files(demo_data_dir: pathlib.Path):
    for _ in range(0, random.randint(3, 6)):
        timestamp = random_datetime().strftime("%Y%m%d_%H%M%S")
        file_path = demo_data_dir / f"note_{timestamp}.txt"
        with file_path.open("w") as f:
            f.write(random_text())


def create_demo_markdown_files(demo_data_dir: pathlib.Path):
    for _ in range(0, random.randint(3, 6)):
        timestamp = random_datetime().strftime("%Y%m%d_%H%M%S")
        file_path = demo_data_dir / f"note_{timestamp}.md"
        with file_path.open("w") as f:
            f.write(
                random_text(
                    "markdown",
                    additional_instructions="Your text should start with a level one heading.",
                ),
            )


def create_demo_audio_files(demo_data_dir: pathlib.Path):
    for _ in range(0, random.randint(3, 6)):
        timestamp = random_datetime().strftime("%Y%m%d_%H%M%S")
        file_path = demo_data_dir / f"note_{timestamp}.wav"
        text = random_text()
        subprocess.run(
            ["pico2wave", "--lang", "en-US", "--wave", str(file_path), text],
            check=True,
        )


def create_demo_image_files(demo_data_dir: pathlib.Path):
    for _ in range(0, random.randint(3, 6)):
        timestamp = random_datetime().strftime("%Y%m%d_%H%M%S")
        file_path = demo_data_dir / f"photo_{timestamp}.jpg"

        width = random.randint(300, 600)
        height = random.randint(300, 600)

        request_url = f"https://picsum.photos/{width}/{height}"
        response = requests.get(request_url, allow_redirects=True)
        response.raise_for_status()
        with open(file_path, "wb") as f:
            f.write(response.content)


def create_demo_map_files(demo_data_dir: pathlib.Path):
    timestamp = random_datetime()
    file_path = demo_data_dir / "map.gpx"

    location = random_coords()

    trackpoints = []
    for _ in range(random.randint(5, 15)):
        trackpoints.append(
            '<trkpt lat="{}" lon="{}"><time>{}</time></trkpt>'.format(
                location[0] + random.uniform(-0.1, 0.1),
                location[1] + random.uniform(-0.1, 0.1),
                timestamp.isoformat() + "Z",
            ),
        )

    nl = "\n"
    gpx_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<gpx version="1.1" creator="mkmapdiary - https://github.com/jannakl/mkmapdiary">
<wpt lat="{location[0]}" lon="{location[1]}">
<name>Random Point</name>
<time>{timestamp.isoformat()}Z</time>
</wpt>
<trk>
<name>Random Track</name>
<trkseg>
    {nl.join(trackpoints)}
</trkseg>
</trk>
</gpx>
"""
    with open(file_path, "w") as f:
        f.write(gpx_content)


def random_coords():
    lat = random.uniform(-90.0, 90.0)
    lon = random.uniform(-180.0, 180.0)
    return (lat, lon)


def random_text(text_format="plain text", additional_instructions=""):
    location = random_place()
    prompt = f"""Generate a short travel diary entry about visiting {location}.
    One paragraph, use {text_format}.
    Do not explain. Do not include phrases like "Here is" etc.
    {additional_instructions}
    """
    response = ollama.chat(
        model="llama3:8b",
        messages=[{"role": "user", "content": prompt}],
    )
    return response["message"]["content"].strip()


def random_place():
    return random.choice(
        [
            "Hades",
            "Atlantis",
            "El Dorado",
            "Shangri-La",
            "Camelot",
            "Avalon",
            "Narnia",
            "Fairyland",
        ],
    )


def random_datetime():
    start = datetime.datetime(2020, 1, 1)
    end = datetime.datetime(2020, 1, 5)
    delta = end - start
    random_days = random.randint(0, delta.days)
    random_seconds = random.randint(0, 86400)
    return start + datetime.timedelta(days=random_days, seconds=random_seconds)


@click.command()
@click.argument(
    "source_dir",
    type=click.Path(path_type=pathlib.Path),
    required=True,
)
def generate_demo(source_dir):
    """Generate demo data in the source directory.

    This command generates demo data for testing purposes only.
    The target directory must be empty.

    SOURCE_DIR: Directory where demo data will be generated (must be empty)
    """
    if not source_dir:
        raise click.BadParameter("Source directory is required.")

    generate_demo_data(source_dir)
