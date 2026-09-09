import re
from typing import Optional

_FIRST_NUMBER = re.compile(r"(\d+(?:\.\d+)?)")


class ExtentTolerance:
    """Compares two extents written to different conventions.

    An extent is printed as prose — '267 sq. yds', '400 Sq. Yards (334.45 Sq.
    Metres)' — so the leading number is what carries the meaning and the rest is
    units and restatement. Comparison is numeric within a tolerance rather than
    textual, because '267' and '267.00' describe the same plot.
    """

    @staticmethod
    def read_extent(value: Optional[str]) -> Optional[float]:
        match = _FIRST_NUMBER.search(str(value or "").replace(",", ""))
        if match is None:
            return None
        try:
            return float(match.group(1))
        except ValueError:
            return None

    @classmethod
    def agree(
        cls, extent: Optional[str], comparison_extent: Optional[str], tolerance: float
    ) -> bool:
        read = cls.read_extent(extent)
        comparison = cls.read_extent(comparison_extent)
        if read is None or comparison is None:
            return False
        return abs(read - comparison) < tolerance
