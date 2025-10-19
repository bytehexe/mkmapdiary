import os
import pathlib
import click
import random
import datetime
import sys
import ollama


def generate_demo_data(demo_data_dir: pathlib.Path):
    if not demo_data_dir.exists():
        demo_data_dir.mkdir(parents=True, exist_ok=True)
    elif any(demo_data_dir.iterdir()):
        click.echo(
            f"Source directory '{demo_data_dir}' must be empty to generate demo data."
        )
        sys.exit(1)

    click.echo(f"Generating demo data in '{demo_data_dir}' ...")

    create_demo_text_files(demo_data_dir)
    create_demo_markdown_files(demo_data_dir)
    # create_demo_audio_files(demo_data_dir)
    # create_demo_image_files(demo_data_dir)
    # create_demo_map_files(demo_data_dir)


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
                )
            )


def random_text(format="plain text", additional_instructions=""):
    location = random_place()
    prompt = f"""Generate a short travel diary entry about visiting {location}.
    One paragraph, use {format}.
    Do not explain. Do not include phrases like "Here is" etc.
    {additional_instructions}
    """
    response = ollama.chat(
        model="llama3:8b", messages=[{"role": "user", "content": prompt}]
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
        ]
    )


def random_datetime():
    start = datetime.datetime(2020, 1, 1)
    end = datetime.datetime(2020, 1, 5)
    delta = end - start
    random_days = random.randint(0, delta.days)
    random_seconds = random.randint(0, 86400)
    return start + datetime.timedelta(days=random_days, seconds=random_seconds)
