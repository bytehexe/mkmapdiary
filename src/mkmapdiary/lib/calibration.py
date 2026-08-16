from typing import Any, NamedTuple


class Calibration(NamedTuple):
    timezone: str
    offset: int
    effects: list[str] = []
    creator: str | None = None


def resolve(data: dict[str, Any], parent: Calibration) -> Calibration:
    """Resolve a calibration.yaml payload against the enclosing calibration.

    Keys absent from `data` are inherited from `parent`. A key present with a
    null value is an explicit override, not an inheritance — that is how a
    subdirectory clears a creator it would otherwise inherit.
    """
    calibration = data.get("calibration", {})
    return Calibration(
        timezone=calibration.get("timezone", parent.timezone),
        offset=calibration.get("offset", parent.offset),
        effects=data.get("effects", parent.effects),
        creator=data.get("creator", parent.creator),
    )
