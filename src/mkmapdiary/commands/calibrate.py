import logging
import tempfile
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import click
import humanfriendly
import jsonschema
import whenever
import yaml

from mkmapdiary.lib.asset import AssetRecord
from mkmapdiary.lib.config import load_config_param
from mkmapdiary.lib.dirs import Dirs
from mkmapdiary.taskList import TaskList

logger = logging.getLogger(__name__)


@click.group()
def calibrate() -> None:
    """Calibrate camera timestamps."""
    pass


@click.command()
@click.option(
    "--camera-tz",
    type=str,
    default="localtime",
    help='Timezone of the camera timestamps (e.g., "Europe/Berlin" or "Etc/GMT-1"). Defaults to the system localtime.',
)
@click.option(
    "--ref-tz",
    type=str,
    default="localtime",
    help='Timezone of the reference timestamp (e.g., "Europe/Berlin" or "Etc/GMT-1"). Defaults to the system localtime.',
)
@click.option(
    "--output",
    "-o",
    type=click.Path(path_type=Path),
    required=False,
    help="Path to the output file.",
)
@click.option(
    "-n", "--dry-run", is_flag=True, help="Perform a dry run without writing output."
)
@click.argument("image", type=click.Path(path_type=Path), required=True)
@click.argument("ref_time", type=str, required=True)
def file(
    camera_tz: str, ref_tz: str, image: Path, ref_time: str, output: Path, dry_run: bool
) -> None:
    """Calibrate camera timestamps using a reference file."""

    try:
        ZoneInfo(camera_tz)
    except ZoneInfoNotFoundError:
        logger.error(f"Invalid camera timezone: {camera_tz}")
        return

    try:
        ZoneInfo(ref_tz)
    except ZoneInfoNotFoundError:
        logger.error(f"Invalid reference timezone: {ref_tz}")
        return

    with tempfile.TemporaryDirectory() as tempdir:
        tempdir_path = Path(tempdir)
        dirs = Dirs(tempdir_path, tempdir_path, tempdir_path, False)

        config = load_config_param("site.timezone=UTC")
        taskList = TaskList(config, dirs, dict(), scan=False)
        assets = list(taskList.handle_path(image))
        if not assets:
            logger.error("No assets found in the specified image.")
            return

    asset: AssetRecord = assets[0]

    if asset.timestamp_utc is None:
        logger.error("Could not extract timestamp from the image.")
        return

    wz_camera_time: whenever.ZonedDateTime = (
        asset.timestamp_utc.to_fixed_offset(0).to_plain().assume_tz(camera_tz)
    )
    wz_ref_time: whenever.ZonedDateTime = whenever.PlainDateTime(
        *humanfriendly.parse_date(ref_time)
    ).assume_tz(ref_tz)

    wi_camera_time: whenever.Instant = wz_camera_time.to_instant()
    wi_ref_time: whenever.Instant = wz_ref_time.to_instant()

    logger.info(f"Camera time         : {wz_camera_time}")
    logger.info(f"Reference time      : {wz_ref_time}")
    logger.info(f"Camera time (UTC)   : {wi_camera_time}")
    logger.info(f"Reference time (UTC): {wi_ref_time}")

    offset_seconds = int((wi_camera_time - wi_ref_time).in_seconds())
    offset_minutes = round(offset_seconds / 60)
    logger.info(
        f"Calculated offset   : {offset_seconds} seconds (about {offset_minutes} minutes)",
        extra={"icon": "🛠️"},
    )

    if abs(offset_seconds) >= 60 * 60:  # more than one hour
        logger.warning(
            "The calculated offset is more than one hour. Please verify that the timezones are correct."
        )

    if output is None:
        output = image.parent / "calibration.yaml"
    elif output.is_dir():
        output = output / "calibration.yaml"

    data = {
        "calibration": {
            "timezone": camera_tz,
            "offset": offset_seconds,
        }
    }

    write_calibration_data(data, output, dry_run)


def write_calibration_data(data: dict, output: Path, dry_run: bool) -> None:
    schema_path = Path(__file__).parent.parent / "resources" / "calibrate_schema.yaml"
    with schema_path.open() as f:
        schema = yaml.safe_load(f)

    jsonschema.validate(instance=data, schema=schema)

    if dry_run:
        logger.info(f"Dry run enabled; would write to {output}:", extra={"icon": "😎"})
        return

    # Load existing data if file exists, otherwise start with empty dict
    existing_data: dict[str, Any] = {}
    if output.exists():
        try:
            with output.open("r", encoding="utf-8") as f:
                existing_data = yaml.safe_load(f) or {}
        except Exception as e:
            logger.warning(f"Could not read existing calibration file {output}: {e}")
            existing_data = {}

    # Merge the calibration data, preserving other keys
    existing_data.update(data)

    with output.open("w", encoding="utf-8") as f:
        yaml.dump(existing_data, f, sort_keys=False)

    logger.info(f"Calibration data written to {output}", extra={"icon": "💾"})


@click.command()
@click.option("-o", "--output", type=click.Path(path_type=Path), required=True)
@click.option("-x", "--offset", type=int, default=0, help="Offset in seconds.")
@click.option(
    "--camera-tz",
    type=str,
    default="localtime",
    help="Timezone of the camera timestamps.",
)
def manual(output: Path, offset: int, camera_tz: str) -> None:
    """Calibrate camera timestamps manually."""

    try:
        ZoneInfo(camera_tz)
    except ZoneInfoNotFoundError:
        logger.error(f"Invalid camera timezone: {camera_tz}")
        return

    data = {
        "calibration": {
            "timezone": camera_tz,
            "offset": offset,
        }
    }

    offset_minutes = round(offset / 60)

    logger.info(f"Camera timezone: {camera_tz}")
    logger.info(
        f"Offset         : {offset} seconds (about {offset_minutes} minutes)",
    )

    if output.is_dir():
        output = output / "calibration.yaml"

    write_calibration_data(data, output, dry_run=False)


@click.command()
@click.option("-o", "--output", type=click.Path(path_type=Path), required=True)
@click.option(
    "--add",
    "effects_to_add",
    multiple=True,
    help="Add effect(s) to the effects list. Can be used multiple times.",
)
@click.option(
    "--remove",
    "effects_to_remove",
    multiple=True,
    help="Remove effect(s) from the effects list. Can be used multiple times.",
)
@click.option(
    "-n", "--dry-run", is_flag=True, help="Perform a dry run without writing output."
)
def effects(
    output: Path,
    effects_to_add: tuple[str, ...],
    effects_to_remove: tuple[str, ...],
    dry_run: bool,
) -> None:
    """Manage effects in calibration file."""

    if not effects_to_add and not effects_to_remove:
        logger.error("You must specify at least one effect to add or remove.")
        return

    if output.is_dir():
        output = output / "calibration.yaml"

    # Load existing data if file exists, otherwise start with empty dict
    existing_data: dict[str, Any] = {}
    if output.exists():
        try:
            with output.open("r", encoding="utf-8") as f:
                existing_data = yaml.safe_load(f) or {}
        except Exception as e:
            logger.warning(f"Could not read existing calibration file {output}: {e}")
            existing_data = {}

    # Get current effects list or create empty list
    current_effects = existing_data.get("effects", [])
    if not isinstance(current_effects, list):
        logger.warning("Existing effects is not a list, creating new effects list.")
        current_effects = []

    # Add new effects
    for effect in effects_to_add:
        if effect not in current_effects:
            current_effects.append(effect)
            logger.info(f"Added effect: {effect}")
        else:
            logger.warning(f"Effect '{effect}' already exists in the list.")

    # Remove effects
    for effect in effects_to_remove:
        if effect in current_effects:
            current_effects.remove(effect)
            logger.info(f"Removed effect: {effect}")
        else:
            logger.warning(f"Effect '{effect}' not found in the list.")

    # Update the effects in the data
    data = {"effects": current_effects}

    # Use the shared write function for consistency and validation
    write_calibration_data(data, output, dry_run)

    if not dry_run:
        logger.info(f"Current effects: {current_effects}")


calibrate.add_command(file)
calibrate.add_command(manual)
calibrate.add_command(effects)
