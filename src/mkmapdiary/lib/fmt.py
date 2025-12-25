import whenever

from .asset import AssetRecord


def time_string(
    asset_data: AssetRecord, current_date: whenever.Date | None
) -> tuple[str, str]:
    """Convert asset_time to a formatted time string in the local timezone of current_date."""
    # Use timestamp_geo if available, fall back to timestamp_utc
    timestamp_obj = asset_data.timestamp_geo or asset_data.timestamp_utc

    if timestamp_obj:
        # Format time
        obj_dt = timestamp_obj.py_datetime()
        # Include day name if timestamp is from a different date
        if current_date is None:
            time_str = obj_dt.strftime("%c")
        elif (
            obj_dt.year != current_date.year
            or obj_dt.month != current_date.month
            or obj_dt.day != current_date.day
        ):
            time_str = obj_dt.strftime("%c")
        else:
            time_str = obj_dt.strftime("%X")

        # Extract timezone info
        if asset_data.timestamp_geo and hasattr(asset_data.timestamp_geo, "tz"):
            timezone_str = str(asset_data.timestamp_geo.tz)
        else:
            timezone_str = "UTC"
    else:
        time_str = ""
        timezone_str = ""

    return time_str, timezone_str


def location_string(asset_data: AssetRecord) -> str | None:
    """Get location string from asset_data's latitude and longitude."""

    if (
        asset_data is not None
        and asset_data.latitude is not None
        and asset_data.longitude is not None
    ):
        # Type assertions since we've checked asset_data is not None
        latitude = asset_data.latitude
        longitude = asset_data.longitude
        assert isinstance(latitude, (int, float)), "Latitude should be numeric"
        assert isinstance(longitude, (int, float)), "Longitude should be numeric"

        north_south = "N" if latitude >= 0 else "S"
        east_west = "E" if longitude >= 0 else "W"
        location = (
            f"{abs(latitude):.4f}° {north_south}, {abs(longitude):.4f}° {east_west}"
        )
    else:
        location = None

    return location
