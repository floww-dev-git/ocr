import math


def round_half_up(value: float, decimal_places: int) -> float:
    # Ties go away from zero, matching JavaScript's Math.round; Python's
    # built-in round() is half-even and disagrees on exact .5 boundaries.
    scale = 10**decimal_places
    return math.floor(value * scale + 0.5) / scale
