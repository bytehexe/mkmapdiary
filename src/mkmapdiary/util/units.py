def format_time(seconds: float) -> str:
    """Rough time formatting from seconds to # (s|min|h|d) # (s|min|h)"""
    if seconds < 60:
        return f"{seconds:.0f} s"
    minutes = seconds / 60
    if minutes < 60:
        seconds_left = int(seconds % 60)
        return f"{int(minutes)} min {seconds_left:02d} s"
    hours = minutes / 60
    if hours < 24:
        minutes_left = int(minutes % 60)
        return f"{int(hours)} h {minutes_left:02d} min"
    days = hours / 24
    hours_left = int(hours % 24)
    return f"{int(days)} d {hours_left} h"


def format_distance(meters: float) -> str:
    """Rough distance formatting from meters to #.## (unit)"""
    if meters < 1000:
        return f"{meters:.2f} m"
    kilometers = meters / 1000
    return f"{kilometers:.2f} km"
