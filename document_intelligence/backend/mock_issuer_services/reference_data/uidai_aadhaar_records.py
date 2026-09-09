from dataclasses import dataclass
from typing import Mapping


@dataclass(frozen=True)
class UidaiAadhaarRecord:
    aadhaar_number: str
    registered_name: str
    date_of_birth: str
    gender: str


# What UIDAI holds for the three seeded applications. Each agrees with the
# application form, so the demographic check confirms and any disagreement the
# officer sees comes from the card being misread rather than from seeded noise.
UIDAI_AADHAAR_RECORDS_BY_NUMBER: Mapping[str, UidaiAadhaarRecord] = {
    "731655204821": UidaiAadhaarRecord(
        aadhaar_number="731655204821",
        registered_name="SRINIVAS RAO KANDULA",
        date_of_birth="1979-08-14",
        gender="Male",
    ),
    "409322107754": UidaiAadhaarRecord(
        aadhaar_number="409322107754",
        registered_name="LAKSHMI PRASANNA DEVARAKONDA",
        date_of_birth="1986-02-03",
        gender="Female",
    ),
    "551809326604": UidaiAadhaarRecord(
        aadhaar_number="551809326604",
        registered_name="MOHAMMED IRFAN SIDDIQUI",
        date_of_birth="1982-11-27",
        gender="Male",
    ),
    # The clean happy path (BN/2026/0512). Agrees with the Aadhaar as printed.
    "255947716541": UidaiAadhaarRecord(
        aadhaar_number="255947716541",
        registered_name="CHENNA SIVA SANKAR",
        date_of_birth="1999-10-28",
        gender="Male",
    ),
    # The Aadhaar capability showcase (BN/2026/0601, ADR-013). UIDAI holds the clean
    # identity, so the clean specimen confirms end to end. The tampered specimen's
    # altered number is deliberately NOT here: the department has no record of it,
    # which is the right answer for a number that was never issued.
    "234567890124": UidaiAadhaarRecord(
        aadhaar_number="234567890124",
        registered_name="RITHIKA SHARMA",
        date_of_birth="1990-06-15",
        gender="Female",
    ),
    # The wrong-person specimen carries a real (Verhoeff-valid) number for a
    # different identity, and UIDAI confirms that identity — so the demographic
    # check agrees while the cross-check against the application is what fails.
    "567890123458": UidaiAadhaarRecord(
        aadhaar_number="567890123458",
        registered_name="VIKRAM ANAND REDDY",
        date_of_birth="1985-02-09",
        gender="Male",
    ),
}
