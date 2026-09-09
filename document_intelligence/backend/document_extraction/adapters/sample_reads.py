from dataclasses import dataclass
from typing import Mapping, Optional, Tuple

from document_catalog.constants.enums import DocumentTypeEnum
from document_extraction.adapters.deed_sample_reads import (
    BOX_BY_FIELD_KEY,
    CONFIDENCE_BY_FIELD_KEY,
    DEED_SAMPLE_READS,
    DeedSampleSpec,
)
from document_extraction.adapters.reads.deed_read import (
    LINK_DOCUMENT_READ,
    SALE_DEED_READ,
)
from document_extraction.dtos.deed_record_dtos import DeedRecordDTO
from document_extraction.dtos.document_record_dtos import DocumentQualityDTO

# Taken from each type's own read spec so the canned reads and the real reads emit
# exactly the same field keys.
DEED_FIELD_KEYS_BY_DOCUMENT_TYPE = {
    SALE_DEED_READ.document_type_id: tuple(
        SALE_DEED_READ.field_keys_by_attribute.values()
    ),
    LINK_DOCUMENT_READ.document_type_id: tuple(
        LINK_DOCUMENT_READ.field_keys_by_attribute.values()
    ),
}
DEED_STRUCTURE_BY_DOCUMENT_TYPE = {
    SALE_DEED_READ.document_type_id: {
        structure_key: True
        for structure_key in SALE_DEED_READ.structure_keys_by_attribute.values()
    },
    LINK_DOCUMENT_READ.document_type_id: {
        structure_key: True
        for structure_key in LINK_DOCUMENT_READ.structure_keys_by_attribute.values()
    },
}


@dataclass(frozen=True)
class SampleFieldRead:
    key: str
    value: str
    confidence: float
    box: Tuple[int, int, int, int]


@dataclass(frozen=True)
class DocumentSampleRead:
    filename: str
    file_format: str
    file_size_bytes: int
    type_confidence: float
    page_count: int
    field_reads: Tuple[SampleFieldRead, ...]
    structure_findings: Mapping[str, bool]
    # Only a registered property document carries one, and the offline demo needs it:
    # without it the chain engine would have nothing to reason over in mock mode.
    deed_record: Optional[DeedRecordDTO] = None
    # What a QR on the document carries, authored so the QR-vs-print check still
    # demonstrates on the fallback path where there is no image to decode. None for
    # every legacy sample, so the check stays absent for them exactly as before.
    qr_fields: Optional[Mapping[str, str]] = None
    # An authored legibility verdict for the fallback path. None leaves the quality
    # check absent, matching legacy behaviour.
    quality: Optional[DocumentQualityDTO] = None


_PAN_STRUCTURE: Mapping[str, bool] = {
    "photo": True,
    "signature": True,
    "hologram": True,
}
_AADHAAR_STRUCTURE: Mapping[str, bool] = {
    "photo": True,
    "qr": True,
    "emblem": True,
}
_LICENCE_STRUCTURE: Mapping[str, bool] = {
    "photo": True,
    "hologram": True,
}
_CLEARANCE_LETTER_STRUCTURE: Mapping[str, bool] = {
    "seal": True,
    "signature": True,
}

_NAME_BOX = (222, 386, 268, 792)
_PARENT_NAME_BOX = (296, 386, 342, 812)
_DATE_OF_BIRTH_BOX = (370, 386, 414, 616)
_PAN_BOX = (446, 386, 498, 704)

_GENDER_BOX = (370, 640, 414, 780)
_AADHAAR_NUMBER_BOX = (520, 300, 580, 820)
_ADDRESS_BOX = (600, 300, 700, 900)

_LICENCE_NUMBER_BOX = (180, 300, 240, 760)
_VALID_UNTIL_BOX = (440, 300, 494, 620)
_BLOOD_GROUP_BOX = (440, 660, 494, 780)

# A clearance letter, not a card: the reference block sits under the letterhead,
# the substance in the body, the validity in the conditions below it.
_ISSUED_BY_BOX = (58, 240, 112, 760)
_NOC_NUMBER_BOX = (152, 88, 196, 470)
_ISSUE_DATE_BOX = (152, 620, 196, 906)
_NOC_APPLICANT_BOX = (268, 200, 312, 704)
_NOC_SURVEY_NUMBER_BOX = (340, 296, 384, 558)
_BUFFER_CONDITION_BOX = (556, 88, 638, 910)
_NOC_VALID_UNTIL_BOX = (642, 88, 686, 520)

# Revenue-side documents: a stacked block of labelled rows. One reusable ladder of
# rows, since these are canned provenance rectangles rather than reads of a real
# page — the mapper only needs them present and within 0-1000.
_LAND_ROW_1 = (120, 300, 164, 760)
_LAND_ROW_2 = (176, 300, 220, 760)
_LAND_ROW_3 = (232, 300, 276, 760)
_LAND_ROW_4 = (288, 300, 332, 760)
_LAND_ROW_5 = (344, 300, 388, 760)
_LAND_ROW_6 = (400, 300, 444, 760)
_LAND_ROW_7 = (456, 300, 500, 760)
_LAND_ROW_8 = (512, 300, 556, 760)
_LAND_ROW_9 = (568, 300, 612, 760)

CLEAN_APPLICATION_ID = "BN/2026/0421"
SECOND_APPLICATION_ID = "BN/2026/0398"
MISMATCH_APPLICATION_ID = "BN/2026/0377"

_IDENTITY_SAMPLE_READS: Mapping[Tuple[str, str], DocumentSampleRead] = {
    (CLEAN_APPLICATION_ID, DocumentTypeEnum.PAN.value): DocumentSampleRead(
        filename="pan_card.pdf",
        file_format="PDF",
        file_size_bytes=188000,
        type_confidence=0.99,
        page_count=1,
        field_reads=(
            SampleFieldRead("name", "SRINIVAS RAO KANDULA", 0.98, _NAME_BOX),
            SampleFieldRead(
                "parentName", "VENKATESWARA RAO KANDULA", 0.96, _PARENT_NAME_BOX
            ),
            SampleFieldRead("dob", "1979-08-14", 0.99, _DATE_OF_BIRTH_BOX),
            SampleFieldRead("pan", "DQRPK4831L", 0.99, _PAN_BOX),
        ),
        structure_findings=_PAN_STRUCTURE,
    ),
    (SECOND_APPLICATION_ID, DocumentTypeEnum.PAN.value): DocumentSampleRead(
        filename="pan.jpg",
        file_format="JPEG",
        file_size_bytes=260000,
        type_confidence=0.97,
        page_count=1,
        field_reads=(
            SampleFieldRead("name", "LAKSHMI PRASANNA DEVARAKONDA", 0.97, _NAME_BOX),
            SampleFieldRead(
                "parentName", "RAMESH BABU DEVARAKONDA", 0.95, _PARENT_NAME_BOX
            ),
            SampleFieldRead("dob", "1986-02-03", 0.98, _DATE_OF_BIRTH_BOX),
            SampleFieldRead("pan", "AKLPD2291Q", 0.99, _PAN_BOX),
        ),
        structure_findings=_PAN_STRUCTURE,
    ),
    (MISMATCH_APPLICATION_ID, DocumentTypeEnum.PAN.value): DocumentSampleRead(
        filename="pan_irfan.pdf",
        file_format="PDF",
        file_size_bytes=176000,
        type_confidence=0.98,
        page_count=1,
        field_reads=(
            # The seeded misread: one letter dropped from the surname.
            SampleFieldRead("name", "MOHAMMED IRFAN SIDDIQI", 0.95, _NAME_BOX),
            SampleFieldRead(
                "parentName", "MOHAMMED YOUSUF SIDDIQUI", 0.95, _PARENT_NAME_BOX
            ),
            SampleFieldRead("dob", "1982-11-27", 0.98, _DATE_OF_BIRTH_BOX),
            SampleFieldRead("pan", "BNMPS7720K", 0.99, _PAN_BOX),
        ),
        structure_findings=_PAN_STRUCTURE,
    ),
    (CLEAN_APPLICATION_ID, DocumentTypeEnum.AADHAAR.value): DocumentSampleRead(
        filename="aadhaar_front.jpg",
        file_format="JPEG",
        file_size_bytes=412000,
        type_confidence=0.98,
        page_count=1,
        field_reads=(
            SampleFieldRead("name", "Srinivas Rao Kandula", 0.97, _NAME_BOX),
            SampleFieldRead("dob", "1979-08-14", 0.99, _DATE_OF_BIRTH_BOX),
            SampleFieldRead("gender", "Male", 0.99, _GENDER_BOX),
            SampleFieldRead(
                "aadhaarNo", "731655204821", 0.99, _AADHAAR_NUMBER_BOX
            ),
            # The seeded address disagreement: the card still carries the holder's
            # previous address in Banjara Hills, the application the new plot.
            SampleFieldRead(
                "address",
                "H.No 8-2-293/82, Road No 12, Banjara Hills, Hyderabad 500034",
                0.93,
                _ADDRESS_BOX,
            ),
        ),
        structure_findings=_AADHAAR_STRUCTURE,
    ),
    (SECOND_APPLICATION_ID, DocumentTypeEnum.AADHAAR.value): DocumentSampleRead(
        filename="aadhaar.pdf",
        file_format="PDF",
        file_size_bytes=310000,
        type_confidence=0.98,
        page_count=1,
        field_reads=(
            SampleFieldRead("name", "Lakshmi Prasanna Devarakonda", 0.97, _NAME_BOX),
            SampleFieldRead("dob", "1986-02-03", 0.99, _DATE_OF_BIRTH_BOX),
            SampleFieldRead("gender", "Female", 0.99, _GENDER_BOX),
            SampleFieldRead(
                "aadhaarNo", "409322107754", 0.99, _AADHAAR_NUMBER_BOX
            ),
            SampleFieldRead(
                "address",
                "H.No 3-45, Ameenpur, Sangareddy 502032",
                0.95,
                _ADDRESS_BOX,
            ),
        ),
        structure_findings=_AADHAAR_STRUCTURE,
    ),
    (
        CLEAN_APPLICATION_ID,
        DocumentTypeEnum.DRIVING_LICENCE.value,
    ): DocumentSampleRead(
        filename="driving_licence.pdf",
        file_format="PDF",
        file_size_bytes=240000,
        type_confidence=0.96,
        page_count=2,
        field_reads=(
            SampleFieldRead("name", "Srinivas Rao Kandula", 0.95, _NAME_BOX),
            # The seeded disagreement: the licence was issued against a year of
            # birth one out from the one on the application form.
            SampleFieldRead("dob", "1978-08-14", 0.91, _DATE_OF_BIRTH_BOX),
            SampleFieldRead(
                "dlNo", "TS0920150012345", 0.97, _LICENCE_NUMBER_BOX
            ),
            SampleFieldRead("validUpto", "2035-06-30", 0.96, _VALID_UNTIL_BOX),
            SampleFieldRead(
                "address",
                "Plot 42, Sri Sai Nagar Colony, Bachupally 500090",
                0.90,
                _ADDRESS_BOX,
            ),
            SampleFieldRead("bloodGroup", "B+", 0.88, _BLOOD_GROUP_BOX),
        ),
        structure_findings=_LICENCE_STRUCTURE,
    ),
    (MISMATCH_APPLICATION_ID, DocumentTypeEnum.AADHAAR.value): DocumentSampleRead(
        filename="aadhaar_irfan.jpg",
        file_format="JPEG",
        file_size_bytes=398000,
        type_confidence=0.97,
        page_count=1,
        field_reads=(
            SampleFieldRead("name", "Mohammed Irfan Siddiqui", 0.96, _NAME_BOX),
            SampleFieldRead("dob", "1982-11-27", 0.99, _DATE_OF_BIRTH_BOX),
            SampleFieldRead("gender", "Male", 0.99, _GENDER_BOX),
            SampleFieldRead(
                "aadhaarNo", "551809326604", 0.99, _AADHAAR_NUMBER_BOX
            ),
            SampleFieldRead(
                "address",
                "H.No 12-2-831/4, Mehdipatnam, Hyderabad 500028",
                0.94,
                _ADDRESS_BOX,
            ),
        ),
        structure_findings=_AADHAAR_STRUCTURE,
    ),
    # The showcase applicant's PAN (BN/2026/0601, ADR-013). It agrees with the
    # application and with the clean Aadhaar, so on its own it simply verifies. Its
    # reason for being here is the cross-document scenario: filed alongside a
    # different person's Aadhaar (aadhaar_mismatch.pdf), the name reconciliation
    # across the two identity documents fails. A PAN is keyed by application here,
    # not by filename, because the showcase holds only one PAN.
    ("BN/2026/0601", DocumentTypeEnum.PAN.value): DocumentSampleRead(
        filename="pan_rithika.pdf",
        file_format="PDF",
        file_size_bytes=184000,
        type_confidence=0.99,
        page_count=1,
        field_reads=(
            SampleFieldRead("name", "RITHIKA SHARMA", 0.98, _NAME_BOX),
            SampleFieldRead(
                "parentName", "ANIL KUMAR SHARMA", 0.96, _PARENT_NAME_BOX
            ),
            SampleFieldRead("dob", "1990-06-15", 0.99, _DATE_OF_BIRTH_BOX),
            SampleFieldRead("pan", "AKRPS4416H", 0.99, _PAN_BOX),
        ),
        structure_findings=_PAN_STRUCTURE,
    ),
}


_CLEARANCE_SAMPLE_READS: Mapping[Tuple[str, str], DocumentSampleRead] = {
    (
        MISMATCH_APPLICATION_ID,
        DocumentTypeEnum.IRRIGATION_NOC.value,
    ): DocumentSampleRead(
        filename="irrigation_noc.pdf",
        file_format="PDF",
        file_size_bytes=290000,
        type_confidence=0.96,
        page_count=2,
        field_reads=(
            SampleFieldRead("nocNo", "IRR/NOC/2026/0093", 0.98, _NOC_NUMBER_BOX),
            SampleFieldRead(
                "issuedBy", "Irrigation and CAD Department", 0.96, _ISSUED_BY_BOX
            ),
            SampleFieldRead("issueDate", "2026-04-10", 0.98, _ISSUE_DATE_BOX),
            SampleFieldRead("validUpto", "2028-04-09", 0.97, _NOC_VALID_UNTIL_BOX),
            SampleFieldRead(
                "applicant", "Mohammed Irfan Siddiqui", 0.95, _NOC_APPLICANT_BOX
            ),
            SampleFieldRead("surveyNo", "77/2", 0.97, _NOC_SURVEY_NUMBER_BOX),
            SampleFieldRead(
                "bufferCondition",
                (
                    "Site lies outside the FTL buffer. No construction within 9 m of "
                    "the tank bund."
                ),
                0.90,
                _BUFFER_CONDITION_BOX,
            ),
        ),
        structure_findings=_CLEARANCE_LETTER_STRUCTURE,
    ),
    (
        CLEAN_APPLICATION_ID,
        DocumentTypeEnum.IRRIGATION_NOC.value,
    ): DocumentSampleRead(
        filename="irrigation_noc_bachupally.pdf",
        file_format="PDF",
        file_size_bytes=264000,
        type_confidence=0.94,
        page_count=2,
        field_reads=(
            SampleFieldRead("nocNo", "IRR/NOC/2024/0518", 0.97, _NOC_NUMBER_BOX),
            SampleFieldRead(
                "issuedBy",
                "Irrigation and CAD Department, Medchal-Malkajgiri",
                0.95,
                _ISSUED_BY_BOX,
            ),
            SampleFieldRead("issueDate", "2024-05-22", 0.97, _ISSUE_DATE_BOX),
            # The seeded disagreement: the NOC ran out in May 2026, before the day
            # this application is being scrutinised, so the clearance has lapsed and
            # a renewal has to be asked for.
            SampleFieldRead("validUpto", "2026-05-21", 0.96, _NOC_VALID_UNTIL_BOX),
            SampleFieldRead(
                "applicant", "Srinivas Rao Kandula", 0.96, _NOC_APPLICANT_BOX
            ),
            SampleFieldRead("surveyNo", "118/2", 0.97, _NOC_SURVEY_NUMBER_BOX),
            SampleFieldRead(
                "bufferCondition",
                (
                    "Site abuts the Bachupally tank foreshore. No construction within "
                    "30 m of the FTL boundary."
                ),
                0.88,
                _BUFFER_CONDITION_BOX,
            ),
        ),
        structure_findings=_CLEARANCE_LETTER_STRUCTURE,
    ),
}


# The revenue-side land documents, all seeded on the near-water-body application
# BN/2026/0377 (applicant Mohammed Irfan Siddiqui, survey 77/2, Kokapet, 420 sq. yd).
# Four read clean and consistent with the application; the pattadar pass book reads
# a smaller extent (390 vs 420), which trips the extent-tolerance rule as a warning —
# a realistic revenue-vs-application discrepancy for the demo to catch.
_LAND_DOCUMENT_SAMPLE_READS: Mapping[Tuple[str, str], DocumentSampleRead] = {
    (
        MISMATCH_APPLICATION_ID,
        DocumentTypeEnum.ENCUMBRANCE_CERTIFICATE.value,
    ): DocumentSampleRead(
        filename="encumbrance_certificate.pdf",
        file_format="PDF",
        file_size_bytes=210000,
        type_confidence=0.95,
        page_count=3,
        field_reads=(
            SampleFieldRead("ecNo", "EC/2026/GDP/04412", 0.97, _LAND_ROW_1),
            SampleFieldRead(
                "period", "01-01-2000 to 31-12-2025", 0.95, _LAND_ROW_2
            ),
            SampleFieldRead("surveyNo", "77/2", 0.97, _LAND_ROW_3),
            SampleFieldRead("owner", "Mohammed Irfan Siddiqui", 0.95, _LAND_ROW_4),
            SampleFieldRead(
                "encumbrances",
                "No subsisting encumbrances found for the period searched.",
                0.9,
                _LAND_ROW_5,
            ),
        ),
        structure_findings={"seal": True, "signature": True},
    ),
    (
        MISMATCH_APPLICATION_ID,
        DocumentTypeEnum.CONVERSION_CERT.value,
    ): DocumentSampleRead(
        filename="land_conversion_certificate.pdf",
        file_format="PDF",
        file_size_bytes=196000,
        type_confidence=0.94,
        page_count=2,
        field_reads=(
            SampleFieldRead(
                "conversionOrderNo", "RDO/NALA/2025/0731", 0.97, _LAND_ROW_1
            ),
            SampleFieldRead(
                "issuedBy",
                "Revenue Divisional Officer, Rajendranagar",
                0.95,
                _LAND_ROW_2,
            ),
            SampleFieldRead("issueDate", "2025-11-18", 0.97, _LAND_ROW_3),
            SampleFieldRead(
                "applicant", "Mohammed Irfan Siddiqui", 0.95, _LAND_ROW_4
            ),
            SampleFieldRead("surveyNo", "77/2", 0.97, _LAND_ROW_5),
            SampleFieldRead("village", "Kokapet", 0.96, _LAND_ROW_6),
            SampleFieldRead("extent", "420 sq. yds", 0.94, _LAND_ROW_7),
            SampleFieldRead("convertedUse", "Commercial", 0.93, _LAND_ROW_8),
            SampleFieldRead("nalaAssessment", "Rs. 1,05,000", 0.9, _LAND_ROW_9),
        ),
        structure_findings={"seal": True, "signature": True},
    ),
    (
        MISMATCH_APPLICATION_ID,
        DocumentTypeEnum.MARKET_VALUE_CERT.value,
    ): DocumentSampleRead(
        filename="market_value_certificate.pdf",
        file_format="PDF",
        file_size_bytes=142000,
        type_confidence=0.93,
        page_count=1,
        field_reads=(
            SampleFieldRead("certificateNo", "MVC/GDP/2026/2287", 0.96, _LAND_ROW_1),
            SampleFieldRead("sro", "SRO Gandipet", 0.95, _LAND_ROW_2),
            SampleFieldRead("issueDate", "2026-05-02", 0.97, _LAND_ROW_3),
            SampleFieldRead("surveyNo", "77/2", 0.97, _LAND_ROW_4),
            SampleFieldRead("village", "Kokapet", 0.96, _LAND_ROW_5),
            SampleFieldRead(
                "marketValuePerSqYd", "Rs. 45,000 per sq. yd", 0.92, _LAND_ROW_6
            ),
            SampleFieldRead("valuationAsOn", "2026-04-01", 0.93, _LAND_ROW_7),
        ),
        structure_findings={"seal": True, "signature": True},
    ),
    (
        MISMATCH_APPLICATION_ID,
        DocumentTypeEnum.PATTADAR_PASSBOOK.value,
    ): DocumentSampleRead(
        filename="pattadar_passbook.pdf",
        file_format="PDF",
        file_size_bytes=228000,
        type_confidence=0.95,
        page_count=2,
        field_reads=(
            SampleFieldRead("passbookNo", "PPB-77-002891", 0.96, _LAND_ROW_1),
            SampleFieldRead("pattadar", "Mohammed Irfan Siddiqui", 0.95, _LAND_ROW_2),
            SampleFieldRead("khataNo", "1842", 0.94, _LAND_ROW_3),
            SampleFieldRead("surveyNo", "77/2", 0.97, _LAND_ROW_4),
            SampleFieldRead("village", "Kokapet", 0.96, _LAND_ROW_5),
            # The seeded discrepancy: the revenue record shows 390 sq. yd where the
            # application claims 420. Within neither the tolerance nor a rounding
            # error, so the extent check warns.
            SampleFieldRead("extent", "390 sq. yds", 0.9, _LAND_ROW_6),
            SampleFieldRead("landClassification", "Patta", 0.93, _LAND_ROW_7),
            SampleFieldRead("issueDate", "2021-07-12", 0.95, _LAND_ROW_8),
        ),
        structure_findings={"photo": True, "seal": True, "signature": True},
    ),
    (
        MISMATCH_APPLICATION_ID,
        DocumentTypeEnum.ORC.value,
    ): DocumentSampleRead(
        filename="occupancy_rights_certificate.pdf",
        file_format="PDF",
        file_size_bytes=174000,
        type_confidence=0.93,
        page_count=2,
        field_reads=(
            SampleFieldRead("orcNo", "RDO/ORC/2024/0155", 0.96, _LAND_ROW_1),
            SampleFieldRead(
                "issuedBy", "Revenue Divisional Officer, Chevella", 0.95, _LAND_ROW_2
            ),
            SampleFieldRead("issueDate", "2024-09-30", 0.97, _LAND_ROW_3),
            SampleFieldRead("occupant", "Mohammed Irfan Siddiqui", 0.95, _LAND_ROW_4),
            SampleFieldRead("surveyNo", "77/2", 0.97, _LAND_ROW_5),
            SampleFieldRead("village", "Kokapet", 0.96, _LAND_ROW_6),
            SampleFieldRead("extent", "420 sq. yds", 0.93, _LAND_ROW_7),
            SampleFieldRead("inamCategory", "Service Inam", 0.9, _LAND_ROW_8),
        ),
        structure_findings={"seal": True, "signature": True},
    ),
}


def build_deed_sample_read(spec: DeedSampleSpec) -> DocumentSampleRead:
    """Turns a deed spec into a canned read, emitting only the fields its type has.

    The field keys come from the type's own read spec, so a link document cannot
    end up carrying a consideration its catalog entry never declared.
    """
    field_values = spec.as_field_values()
    emitted_keys = DEED_FIELD_KEYS_BY_DOCUMENT_TYPE[spec.document_type_id]
    return DocumentSampleRead(
        filename=spec.filename,
        file_format=spec.file_format,
        file_size_bytes=spec.file_size_bytes,
        type_confidence=spec.type_confidence,
        page_count=spec.page_count,
        field_reads=tuple(
            SampleFieldRead(
                field_key,
                field_values[field_key],
                CONFIDENCE_BY_FIELD_KEY[field_key],
                BOX_BY_FIELD_KEY[field_key],
            )
            for field_key in emitted_keys
        ),
        structure_findings=DEED_STRUCTURE_BY_DOCUMENT_TYPE[spec.document_type_id],
        deed_record=spec.as_deed_record(),
    )


SHOWCASE_APPLICATION_ID = "BN/2026/0601"

# The clean applicant, matching application BN/2026/0601 and the clean specimen the
# generator renders. The QR carries the same identity.
_SHOWCASE_NAME = "Rithika Sharma"
_SHOWCASE_NUMBER = "234567890124"  # Verhoeff-valid, matches aadhaar_clean.pdf
_SHOWCASE_DOB = "1990-06-15"
_SHOWCASE_GENDER = "Female"
_SHOWCASE_ADDRESS = (
    "Flat 5B, Lake View Residency, Kondapur, Serilingampally, "
    "Ranga Reddy, Telangana 500084"
)
_SHOWCASE_QR = {
    "name": _SHOWCASE_NAME,
    "aadhaarNo": _SHOWCASE_NUMBER,
    "dob": _SHOWCASE_DOB,
    "gender": _SHOWCASE_GENDER,
}
_GOOD_QUALITY = DocumentQualityDTO(
    score=1.0, blur_score=800.0, resolution_px=615, legible=True
)
_POOR_QUALITY = DocumentQualityDTO(
    score=0.07, blur_score=9.0, resolution_px=615, legible=False
)


def _aadhaar_showcase_read(
    filename: str,
    name: str,
    number: str,
    dob: str,
    gender: str,
    qr_fields,
    quality: DocumentQualityDTO,
) -> DocumentSampleRead:
    return DocumentSampleRead(
        filename=filename,
        file_format="PDF",
        file_size_bytes=240000,
        type_confidence=0.98,
        page_count=2,
        field_reads=(
            SampleFieldRead("name", name, 0.97, _NAME_BOX),
            SampleFieldRead("dob", dob, 0.98, _DATE_OF_BIRTH_BOX),
            SampleFieldRead("gender", gender, 0.98, _GENDER_BOX),
            SampleFieldRead("aadhaarNo", number, 0.99, _AADHAAR_NUMBER_BOX),
            SampleFieldRead("address", _SHOWCASE_ADDRESS, 0.94, _ADDRESS_BOX),
        ),
        structure_findings={"photo": True, "qr": True, "emblem": True},
        qr_fields=qr_fields,
        quality=quality,
    )


# The showcase specimens, keyed by filename because one application (BN/2026/0601)
# holds several different Aadhaar scenarios — so the type-and-application key alone
# cannot tell them apart on the fallback path. Each mirrors what real extraction
# would read off the matching generated PDF.
_AADHAAR_SHOWCASE_READS_BY_FILENAME: Mapping[str, DocumentSampleRead] = {
    "aadhaar_clean.pdf": _aadhaar_showcase_read(
        filename="aadhaar_clean.pdf",
        name=_SHOWCASE_NAME,
        number=_SHOWCASE_NUMBER,
        dob=_SHOWCASE_DOB,
        gender=_SHOWCASE_GENDER,
        qr_fields=dict(_SHOWCASE_QR),
        quality=_GOOD_QUALITY,
    ),
    "aadhaar_tampered_qr.pdf": _aadhaar_showcase_read(
        # Print altered to a different name/number; QR still carries the clean
        # identity, so the QR-vs-print check catches the contradiction. The altered
        # number is itself Verhoeff-valid (matching the generated specimen), so the
        # tamper shows up as the QR contradiction, not as a checksum failure.
        filename="aadhaar_tampered_qr.pdf",
        name="Rithika Verma",
        number="987654321012",
        dob=_SHOWCASE_DOB,
        gender=_SHOWCASE_GENDER,
        qr_fields=dict(_SHOWCASE_QR),
        quality=_GOOD_QUALITY,
    ),
    "aadhaar_invalid_number.pdf": _aadhaar_showcase_read(
        # Twelve digits, valid leading digit, but fails Verhoeff.
        filename="aadhaar_invalid_number.pdf",
        name=_SHOWCASE_NAME,
        number="234567890125",
        dob=_SHOWCASE_DOB,
        gender=_SHOWCASE_GENDER,
        qr_fields={**_SHOWCASE_QR, "aadhaarNo": "234567890125"},
        quality=_GOOD_QUALITY,
    ),
    "aadhaar_mismatch.pdf": _aadhaar_showcase_read(
        # A clean card for a different person than the application declares.
        filename="aadhaar_mismatch.pdf",
        name="Vikram Anand Reddy",
        number="567890123458",
        dob="1985-02-09",
        gender="Male",
        qr_fields={
            "name": "Vikram Anand Reddy",
            "aadhaarNo": "567890123458",
            "dob": "1985-02-09",
            "gender": "Male",
        },
        quality=_GOOD_QUALITY,
    ),
    "aadhaar_poor_scan.pdf": _aadhaar_showcase_read(
        # The clean identity, but a blurred scan — the quality check warns.
        filename="aadhaar_poor_scan.pdf",
        name=_SHOWCASE_NAME,
        number=_SHOWCASE_NUMBER,
        dob=_SHOWCASE_DOB,
        gender=_SHOWCASE_GENDER,
        qr_fields=dict(_SHOWCASE_QR),
        quality=_POOR_QUALITY,
    ),
    "aadhaar_name_typo.pdf": _aadhaar_showcase_read(
        # The printed name drops one letter ('Ritika' for 'Rithika'), a near-match
        # rather than a wrong person. The QR carries the correct spelling, so the
        # QR-vs-print check and the department both treat it as the same person,
        # while the cross-check against the declared application flags it for review.
        filename="aadhaar_name_typo.pdf",
        name="Ritika Sharma",
        number=_SHOWCASE_NUMBER,
        dob=_SHOWCASE_DOB,
        gender=_SHOWCASE_GENDER,
        qr_fields=dict(_SHOWCASE_QR),
        quality=_GOOD_QUALITY,
    ),
    "aadhaar_impossible_dob.pdf": _aadhaar_showcase_read(
        # A future date of birth — the document contradicts itself. The intrinsic
        # consistency check catches it before any comparison. QR carries the same
        # impossible date, so it is a bad document, not a tampered one.
        filename="aadhaar_impossible_dob.pdf",
        name=_SHOWCASE_NAME,
        number=_SHOWCASE_NUMBER,
        dob="2035-01-02",
        gender=_SHOWCASE_GENDER,
        qr_fields={**_SHOWCASE_QR, "dob": "2035-01-02"},
        quality=_GOOD_QUALITY,
    ),
}


# Keyed by (application_id, document_type_id): one canned read per document per
# application, so the offline demo is deterministic and needs no API key. Values are
# carried verbatim from the prototype, including its deliberate disagreements.
SAMPLE_READS_BY_APPLICATION_AND_TYPE: Mapping[Tuple[str, str], DocumentSampleRead] = {
    **_IDENTITY_SAMPLE_READS,
    **_CLEARANCE_SAMPLE_READS,
    **_LAND_DOCUMENT_SAMPLE_READS,
    **{
        (spec.application_id, spec.document_type_id): build_deed_sample_read(spec)
        for spec in DEED_SAMPLE_READS
    },
}


def _showcase_read_for_filename(filename: str) -> Optional[DocumentSampleRead]:
    name = str(filename or "").lower()
    for sample_filename, read in _AADHAAR_SHOWCASE_READS_BY_FILENAME.items():
        if sample_filename in name:
            return read
    return None


def get_sample_read(
    application_id: str,
    document_type_id: Optional[str],
    filename: Optional[str] = None,
) -> Optional[DocumentSampleRead]:
    # A showcase specimen is recognised by its filename first, because one
    # application holds several Aadhaar scenarios that a type key cannot separate.
    showcase = _showcase_read_for_filename(filename or "")
    if showcase is not None:
        return showcase
    return SAMPLE_READS_BY_APPLICATION_AND_TYPE.get(
        (str(application_id or ""), str(document_type_id or ""))
    )
