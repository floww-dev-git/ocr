"""Canned deed reads for the offline demo, carried verbatim from the prototype.

Each seeded application gets a sale deed and the link document behind it, and each
pair is arranged so the sale deed's vendor is the link document's purchaser — which
is what makes the chain of title reconcile.

Structured alongside the flat values because the chain engine reads party lists and
recital citations, and `EXTRACTION_MODE=mock` has to give it the same shape a real
read would.
"""
from dataclasses import dataclass
from typing import Mapping, Optional, Tuple

from document_catalog.constants.enums import DocumentTypeEnum
from document_extraction.dtos.deed_record_dtos import (
    DeedRecordDTO,
    PartyDTO,
    PropertyInfoDTO,
)

SALE_DEED_TYPE = "Sale Deed"

_DOCUMENT_NUMBER_BOX = (140, 300, 190, 700)
_REGISTRATION_DATE_BOX = (140, 720, 190, 940)
_SUB_REGISTRAR_BOX = (200, 300, 250, 760)
_VENDOR_BOX = (300, 300, 350, 820)
_PURCHASER_BOX = (360, 300, 410, 820)
_SURVEY_BOX = (470, 300, 516, 560)
_PLOT_BOX = (470, 600, 516, 760)
_EXTENT_BOX = (530, 300, 576, 620)
_VILLAGE_BOX = (530, 660, 576, 900)
_CONSIDERATION_BOX = (600, 300, 650, 700)
_BOUNDARIES_BOX = (680, 300, 760, 940)

# Per-field read confidences, carried from the prototype. Prose fields read weaker
# than printed identifiers, which is what puts the boundaries and the consideration
# in front of the officer first.
CONFIDENCE_BY_FIELD_KEY: Mapping[str, float] = {
    "docNo": 0.99,
    "regDate": 0.99,
    "sro": 0.97,
    "vendor": 0.95,
    "purchaser": 0.97,
    "surveyNo": 0.99,
    "plotNo": 0.98,
    "extent": 0.94,
    "village": 0.98,
    "consideration": 0.92,
    "boundaries": 0.90,
}

BOX_BY_FIELD_KEY: Mapping[str, Tuple[int, int, int, int]] = {
    "docNo": _DOCUMENT_NUMBER_BOX,
    "regDate": _REGISTRATION_DATE_BOX,
    "sro": _SUB_REGISTRAR_BOX,
    "vendor": _VENDOR_BOX,
    "purchaser": _PURCHASER_BOX,
    "surveyNo": _SURVEY_BOX,
    "plotNo": _PLOT_BOX,
    "extent": _EXTENT_BOX,
    "village": _VILLAGE_BOX,
    "consideration": _CONSIDERATION_BOX,
    "boundaries": _BOUNDARIES_BOX,
}


@dataclass(frozen=True)
class DeedSampleSpec:
    """One canned deed: the values as read, and the record behind them."""

    application_id: str
    document_type_id: str
    filename: str
    file_format: str
    file_size_bytes: int
    type_confidence: float
    page_count: int
    doc_no: str
    registration_date: str
    sro: str
    vendor: str
    purchaser: str
    survey_no: str
    plot_no: str
    extent_text: str
    extent_sq_yard: float
    village: str
    consideration_text: str
    consideration_inr: float
    boundaries: str
    prior_deed_refs: Tuple[str, ...]
    # A deed prints who a party is, not only their name. Supplied where the chain
    # has to tell two people apart; the plain name alone is enough where it does not.
    vendor_party: Optional[PartyDTO] = None
    purchaser_party: Optional[PartyDTO] = None
    execution_date: Optional[str] = None
    stamp_duty_text: Optional[str] = None
    estamp_no: Optional[str] = None

    def as_deed_record(self) -> DeedRecordDTO:
        return DeedRecordDTO(
            doc_no=self.doc_no,
            sro=self.sro,
            registration_date=self.registration_date,
            execution_date=self.execution_date or self.registration_date,
            deed_type=SALE_DEED_TYPE,
            sellers=(self.vendor_party or PartyDTO(name=self.vendor),),
            buyers=(self.purchaser_party or PartyDTO(name=self.purchaser),),
            property_info=PropertyInfoDTO(
                survey_no=self.survey_no,
                plot_no=self.plot_no,
                extent_text=self.extent_text,
                extent_sq_yard=self.extent_sq_yard,
                boundaries=self.boundaries,
                locality=self.village,
            ),
            consideration_text=self.consideration_text,
            consideration_inr=self.consideration_inr,
            stamp_duty_text=self.stamp_duty_text,
            estamp_no=self.estamp_no,
            prior_deed_refs=self.prior_deed_refs,
        )

    def as_field_values(self) -> Mapping[str, str]:
        """The flat values, keyed by catalog field key.

        A link document declares fewer fields than a sale deed, and the ones it does
        not declare are simply never read off this mapping.
        """
        return {
            "docNo": self.doc_no,
            "regDate": self.registration_date,
            "sro": self.sro,
            "vendor": self.vendor,
            "purchaser": self.purchaser,
            "surveyNo": self.survey_no,
            "plotNo": self.plot_no,
            "extent": self.extent_text,
            "village": self.village,
            "consideration": self.consideration_text,
            "boundaries": self.boundaries,
        }


DEED_SAMPLE_READS: Tuple[DeedSampleSpec, ...] = (
    DeedSampleSpec(
        application_id="BN/2026/0421",
        document_type_id=DocumentTypeEnum.SALE_DEED.value,
        filename="sale_deed_2019.pdf",
        file_format="PDF",
        file_size_bytes=3100000,
        type_confidence=0.98,
        page_count=14,
        doc_no="4821/2019",
        registration_date="2019-03-12",
        sro="SRO Quthbullapur",
        vendor="Padmavathi Rentala",
        purchaser="Srinivas Rao Kandula",
        survey_no="118/2",
        plot_no="42",
        extent_text="267 sq. yds",
        extent_sq_yard=267.0,
        village="Bachupally",
        consideration_text="Rs 48,06,000",
        consideration_inr=4806000.0,
        boundaries="North: Plot 41. South: 30 ft road. East: Plot 43. West: Plot 35.",
        prior_deed_refs=("2210/2009",),
    ),
    DeedSampleSpec(
        application_id="BN/2026/0421",
        document_type_id=DocumentTypeEnum.LINK_DOCUMENT.value,
        filename="link_deed_2009.pdf",
        file_format="PDF",
        file_size_bytes=2400000,
        type_confidence=0.95,
        page_count=11,
        doc_no="2210/2009",
        registration_date="2009-07-21",
        sro="SRO Quthbullapur",
        vendor="Bhaskar Reddy Mudireddy",
        purchaser="Padmavathi Rentala",
        survey_no="118/2",
        plot_no="42",
        extent_text="267 sq. yds",
        extent_sq_yard=267.0,
        village="Bachupally",
        consideration_text="Rs 14,20,000",
        consideration_inr=1420000.0,
        boundaries="North: Plot 41. South: 30 ft road. East: Plot 43. West: Plot 35.",
        prior_deed_refs=(),
    ),
    DeedSampleSpec(
        application_id="BN/2026/0398",
        document_type_id=DocumentTypeEnum.SALE_DEED.value,
        filename="sale_deed_2021.pdf",
        file_format="PDF",
        file_size_bytes=2800000,
        type_confidence=0.98,
        page_count=12,
        doc_no="6612/2021",
        registration_date="2021-10-05",
        sro="SRO Patancheru",
        vendor="Nagaraju Bathula",
        purchaser="Lakshmi Prasanna Devarakonda",
        survey_no="232/1",
        plot_no="18",
        extent_text="183 sq. yds",
        extent_sq_yard=183.0,
        village="Ameenpur",
        consideration_text="Rs 36,60,000",
        consideration_inr=3660000.0,
        boundaries="North: Plot 17. South: Plot 19. East: 40 ft road. West: Plot 6.",
        prior_deed_refs=("1105/2012",),
    ),
    DeedSampleSpec(
        application_id="BN/2026/0398",
        document_type_id=DocumentTypeEnum.LINK_DOCUMENT.value,
        filename="link_deed_2012.pdf",
        file_format="PDF",
        file_size_bytes=2100000,
        type_confidence=0.96,
        page_count=10,
        doc_no="1105/2012",
        registration_date="2012-04-18",
        sro="SRO Patancheru",
        vendor="Suresh Kumar Goud",
        purchaser="Nagaraju Bathula",
        survey_no="232/1",
        plot_no="18",
        extent_text="183 sq. yds",
        extent_sq_yard=183.0,
        village="Ameenpur",
        consideration_text="Rs 9,15,000",
        consideration_inr=915000.0,
        boundaries="North: Plot 17. South: Plot 19. East: 40 ft road. West: Plot 6.",
        prior_deed_refs=(),
    ),
    DeedSampleSpec(
        application_id="BN/2026/0377",
        document_type_id=DocumentTypeEnum.SALE_DEED.value,
        filename="sale_deed_2020.pdf",
        file_format="PDF",
        file_size_bytes=3300000,
        type_confidence=0.98,
        page_count=16,
        doc_no="3390/2020",
        registration_date="2020-02-14",
        sro="SRO Gandipet",
        vendor="Kavitha Reddy Pulla",
        purchaser="Mohammed Irfan Siddiqui",
        survey_no="77/2",
        plot_no="9",
        extent_text="420 sq. yds",
        extent_sq_yard=420.0,
        village="Kokapet",
        consideration_text="Rs 1,26,00,000",
        consideration_inr=12600000.0,
        boundaries="North: 60 ft road. South: Plot 10. East: Plot 8. West: Open land.",
        prior_deed_refs=("4471/2011",),
    ),
    DeedSampleSpec(
        application_id="BN/2026/0377",
        document_type_id=DocumentTypeEnum.LINK_DOCUMENT.value,
        filename="link_deed_2011.pdf",
        file_format="PDF",
        file_size_bytes=2600000,
        type_confidence=0.95,
        page_count=12,
        doc_no="4471/2011",
        registration_date="2011-09-09",
        sro="SRO Gandipet",
        vendor="Sattaiah Gurram",
        purchaser="Kavitha Reddy Pulla",
        survey_no="77/2",
        plot_no="9",
        extent_text="420 sq. yds",
        extent_sq_yard=420.0,
        village="Kokapet",
        consideration_text="Rs 42,00,000",
        consideration_inr=4200000.0,
        boundaries="North: 60 ft road. South: Plot 10. East: Plot 8. West: Open land.",
        prior_deed_refs=(),
    ),
)
