import math


def calculate_rank(place=None, radius=None):
    # Use nominatim ranking based on radius as a reference
    # see: https://nominatim.org/release-docs/latest/customize/Ranking/

    if radius is not None:
        rank = int(math.ceil(20 - math.log(radius / 1000, 2)))
        if rank > 23:
            rank = 23
        if rank < 13:
            rank = None
        return rank

    if place in ("city", "municipality", "island"):
        return 13
    if place in ("town", "borough"):
        return 17
    if place in ("village", "suburb", "quarter"):
        return 19
    if place in ("hamlet", "farm", "neighbourhood", "islet"):
        return 20
    if place in ("isolated_dwelling", "city_block"):
        return 21
    if place is None:
        return 23

    return None
