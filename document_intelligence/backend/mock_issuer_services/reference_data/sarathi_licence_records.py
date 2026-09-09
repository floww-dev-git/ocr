from dataclasses import dataclass
from typing import Mapping, Tuple


@dataclass(frozen=True)
class SarathiLicenceRecord:
    licence_number: str
    holder_name: str
    date_of_birth: str
    valid_until: str
    vehicle_classes: Tuple[str, ...]


# What the Transport Department holds. Note the date of birth agrees with the
# licence as printed (1978) rather than with the application form (1979): the
# disagreement the officer has to resolve is between the form and the licence, and
# the department confirms the licence is genuine.
SARATHI_LICENCE_RECORDS_BY_NUMBER: Mapping[str, SarathiLicenceRecord] = {
    "TS0920150012345": SarathiLicenceRecord(
        licence_number="TS0920150012345",
        holder_name="SRINIVAS RAO KANDULA",
        date_of_birth="1978-08-14",
        valid_until="2035-06-30",
        vehicle_classes=("LMV", "MCWG"),
    ),
    # The clean happy path (BN/2026/0512). A sixteen-character number, which is what
    # this office issues; the department agrees with the licence as printed.
    "TS20820220017249": SarathiLicenceRecord(
        licence_number="TS20820220017249",
        holder_name="CHENNA SIVA SANKAR",
        date_of_birth="1999-10-28",
        valid_until="2039-10-28",
        vehicle_classes=("MCWG",),
    ),
}
