from dataclasses import dataclass
from typing import Mapping


@dataclass(frozen=True)
class ItdPanRecord:
    pan: str
    registered_name: str
    date_of_birth: str
    aadhaar_seeded: bool


ITD_PAN_RECORDS_BY_PAN: Mapping[str, ItdPanRecord] = {
    "DQRPK4831L": ItdPanRecord(
        pan="DQRPK4831L",
        registered_name="SRINIVAS RAO KANDULA",
        date_of_birth="1979-08-14",
        aadhaar_seeded=True,
    ),
    "AKLPD2291Q": ItdPanRecord(
        pan="AKLPD2291Q",
        registered_name="LAKSHMI PRASANNA DEVARAKONDA",
        date_of_birth="1986-02-03",
        aadhaar_seeded=True,
    ),
    "BNMPS7720K": ItdPanRecord(
        pan="BNMPS7720K",
        registered_name="MOHAMMED IRFAN SIDDIQUI",
        date_of_birth="1982-11-27",
        aadhaar_seeded=True,
    ),
    # The clean happy path (BN/2026/0512). Agrees with the PAN card as printed.
    "NIUPS5913K": ItdPanRecord(
        pan="NIUPS5913K",
        registered_name="CHENNA SIVA SANKAR",
        date_of_birth="1999-10-28",
        aadhaar_seeded=True,
    ),
}
