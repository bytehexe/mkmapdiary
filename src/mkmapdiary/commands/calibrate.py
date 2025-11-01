import logging
import tempfile
from pathlib import Path

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
@click.argument("image", type=click.Path(path_type=Path), required=True)
@click.argument("ref_time", type=str, required=True)
def calibrate(
    camera_tz: str, ref_tz: str, image: Path, ref_time: str, output: Path
) -> None:
    """Calibrate input files."""

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

    schema_path = Path(__file__).parent.parent / "resources" / "calibrate_schema.yaml"
    with schema_path.open() as f:
        schema = yaml.safe_load(f)

    jsonschema.validate(instance=data, schema=schema)

    with output.open("w", encoding="utf-8") as f:
        yaml.dump(data, f, sort_keys=False)

    logger.info(f"Calibration data written to {output}", extra={"icon": "💾"})
