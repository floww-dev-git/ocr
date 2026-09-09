from dataclasses import dataclass
from typing import Mapping


@dataclass(frozen=True)
class IgrsDeedRecord:
    doc_no: str
    sro: str
    executant: str
    claimant: str
    extent: str
    registration_date: str


# What the registrar holds. Stated here in full rather than derived from the reads
# the rest of the build ships: this app stands in for a separate government system,
# and a fake department that shares a data structure with the system querying it
# cannot show the one thing it exists to show — the two disagreeing.
IGRS_DEED_RECORDS_BY_DOCUMENT_NUMBER: Mapping[str, IgrsDeedRecord] = {
    "4821/2019": IgrsDeedRecord(
        doc_no="4821/2019",
        sro="Quthbullapur",
        executant="PADMAVATHI RENTALA",
        claimant="SRINIVAS RAO KANDULA",
        extent="267 SQ.YDS",
        registration_date="2019-03-12",
    ),
    "2210/2009": IgrsDeedRecord(
        doc_no="2210/2009",
        sro="Quthbullapur",
        executant="BHASKAR REDDY MUDIREDDY",
        claimant="PADMAVATHI RENTALA",
        extent="267 SQ.YDS",
        registration_date="2009-07-21",
    ),
    "6612/2021": IgrsDeedRecord(
        doc_no="6612/2021",
        sro="Patancheru",
        executant="NAGARAJU BATHULA",
        claimant="LAKSHMI PRASANNA DEVARAKONDA",
        extent="183 SQ.YDS",
        registration_date="2021-10-05",
    ),
    "1105/2012": IgrsDeedRecord(
        doc_no="1105/2012",
        sro="Patancheru",
        executant="SURESH KUMAR GOUD",
        claimant="NAGARAJU BATHULA",
        extent="183 SQ.YDS",
        registration_date="2012-04-18",
    ),
    "3390/2020": IgrsDeedRecord(
        doc_no="3390/2020",
        sro="Gandipet",
        executant="KAVITHA REDDY PULLA",
        claimant="MOHAMMED IRFAN SIDDIQUI",
        extent="420 SQ.YDS",
        registration_date="2020-02-14",
    ),
    "4471/2011": IgrsDeedRecord(
        doc_no="4471/2011",
        sro="Gandipet",
        executant="SATTAIAH GURRAM",
        claimant="KAVITHA REDDY PULLA",
        extent="420 SQ.YDS",
        registration_date="2011-09-09",
    ),
    # The three deeds in the bundled files, over Sy. No. 142/2, Plot 17, Kondapur.
    # A register holds one history per registration number, so what is recorded here
    # is the unbroken chain. The bundles that depart from it — a differently
    # transliterated buyer, an extent that grew, a vendor who never bought — depart
    # from this record too, which is the register doing its job.
    "1188/2003": IgrsDeedRecord(
        doc_no="1188/2003",
        sro="Serilingampally",
        executant="GOVIND RAO",
        claimant="RAMESH KUMAR",
        extent="400 SQ.YDS",
        registration_date="2003-06-12",
    ),
    "2451/2011": IgrsDeedRecord(
        doc_no="2451/2011",
        sro="Serilingampally",
        executant="RAMESH KUMAR",
        claimant="SUNITA SHARMA",
        extent="400 SQ.YDS",
        registration_date="2011-09-05",
    ),
    "5820/2019": IgrsDeedRecord(
        doc_no="5820/2019",
        sro="Serilingampally",
        executant="SUNITA SHARMA",
        claimant="PRAKASH IYER",
        extent="400 SQ.YDS",
        registration_date="2019-02-18",
    ),
}
