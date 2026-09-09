import re
from typing import Callable, Dict, Optional, Tuple

from document_catalog.constants.enums import FieldComparisonRule
from document_scrutiny.constants.address_constants import ADDRESS_OVERLAP_PASS_FLOOR
from document_scrutiny.constants.check_thresholds import (
    EXACT_NAME_MATCH,
    NAME_MATCH_WARNING_FLOOR,
)
from document_scrutiny.constants.comparable_application_fields import (
    CHECK_KEYS_BY_APPLICATION_FIELD,
    ComparableApplicationField,
    read_disagreement_status,
)
from document_scrutiny.constants.enums import CheckGroup, CheckStatus
from document_scrutiny.constants.extent_constants import EXTENT_TOLERANCE_SQ_YARD
from document_scrutiny.domain.comparison_rules.address_overlap import AddressOverlap
from document_scrutiny.domain.comparison_rules.extent_tolerance import ExtentTolerance
from document_scrutiny.domain.date_display import format_iso_date
from document_scrutiny.domain.identifier_mask import IdentifierMask
from document_scrutiny.domain.name_similarity import NameSimilarity
from document_scrutiny.dtos.check_dtos import CheckDTO
from document_scrutiny.dtos.field_comparison_dtos import FieldComparisonDTO

NOTHING_READ = "nothing"
PERCENT_SCALE = 100
ADDRESS_ADVISORY = "Addresses change often, so this is advisory."
ADDRESS_AGREES_DETAIL = "Address on the document matches the application."

_NON_ALPHANUMERIC = re.compile(r"[^a-z0-9 ]")

_Comparator = Callable[[FieldComparisonDTO], Tuple[str, str]]


class FieldComparisonChecks:
    @classmethod
    def build(cls, comparison: FieldComparisonDTO) -> CheckDTO:
        compare = cls._comparator_for(comparison)
        status, detail = compare(comparison)
        return cls._build_check(
            comparison=comparison,
            title=cls._title(comparison),
            status=status,
            detail=detail,
        )

    @classmethod
    def _comparator_for(cls, comparison: FieldComparisonDTO) -> _Comparator:
        # The spec's own rule wins where it names one, so a field can be compared
        # by something other than what its application field would imply.
        by_rule = cls._comparators_by_rule().get(str(comparison.comparison_rule or ""))
        if by_rule is not None:
            return by_rule
        return cls._comparators_by_application_field()[comparison.application_field_key]

    @classmethod
    def _comparators_by_rule(cls) -> Dict[str, _Comparator]:
        return {
            FieldComparisonRule.ADDRESS_OVERLAP.value: cls._compare_address,
            FieldComparisonRule.EXTENT_TOLERANCE.value: cls._compare_extent,
        }

    @classmethod
    def _comparators_by_application_field(cls) -> Dict[str, _Comparator]:
        return {
            ComparableApplicationField.APPLICANT_NAME.value: cls._compare_applicant_name,
            ComparableApplicationField.PARENT_NAME.value: cls._compare_parent_name,
            ComparableApplicationField.DATE_OF_BIRTH.value: cls._compare_date,
            ComparableApplicationField.GENDER.value: cls._compare_gender,
            ComparableApplicationField.AADHAAR_NUMBER.value: cls._compare_identifier,
            ComparableApplicationField.PAN.value: cls._compare_identifier,
            ComparableApplicationField.ADDRESS.value: cls._compare_address,
            ComparableApplicationField.SURVEY_NUMBER.value: cls._compare_loose_text,
            ComparableApplicationField.PLOT_NUMBER.value: cls._compare_loose_text,
            ComparableApplicationField.VILLAGE.value: cls._compare_loose_text,
            ComparableApplicationField.EXTENT_SQ_YARD.value: cls._compare_extent,
        }

    @staticmethod
    def _title(comparison: FieldComparisonDTO) -> str:
        titles = {
            ComparableApplicationField.APPLICANT_NAME.value: "Name matches application",
            ComparableApplicationField.PARENT_NAME.value: (
                "Father's name matches application"
            ),
            ComparableApplicationField.DATE_OF_BIRTH.value: (
                "Date of birth matches application"
            ),
            ComparableApplicationField.GENDER.value: "Gender matches application",
            ComparableApplicationField.ADDRESS.value: "Address matches application",
            ComparableApplicationField.SURVEY_NUMBER.value: (
                "Survey number matches application"
            ),
            ComparableApplicationField.PLOT_NUMBER.value: (
                "Plot number matches application"
            ),
            ComparableApplicationField.VILLAGE.value: "Village matches application",
            ComparableApplicationField.EXTENT_SQ_YARD.value: (
                "Extent matches application"
            ),
        }
        return titles.get(
            comparison.application_field_key,
            f"{comparison.field_label} matches application",
        )

    @classmethod
    def _compare_applicant_name(cls, comparison: FieldComparisonDTO) -> Tuple[str, str]:
        status, detail = cls._compare_name(comparison=comparison)
        if status == CheckStatus.PASS.value:
            return status, detail
        similarity = cls._similarity(comparison)
        return status, f"{detail} Similarity {round(similarity * PERCENT_SCALE)}%."

    @classmethod
    def _compare_parent_name(cls, comparison: FieldComparisonDTO) -> Tuple[str, str]:
        return cls._compare_name(comparison=comparison)

    @classmethod
    def _compare_name(cls, comparison: FieldComparisonDTO) -> Tuple[str, str]:
        similarity = cls._similarity(comparison)
        detail = cls._reads_sentence(comparison)
        if similarity == EXACT_NAME_MATCH:
            return CheckStatus.PASS.value, detail
        if similarity >= NAME_MATCH_WARNING_FLOOR:
            return CheckStatus.WARN.value, detail
        return CheckStatus.FAIL.value, detail

    @staticmethod
    def _similarity(comparison: FieldComparisonDTO) -> float:
        return NameSimilarity.calculate(
            name=comparison.read_value, comparison_name=comparison.application_value
        )

    @classmethod
    def _compare_date(cls, comparison: FieldComparisonDTO) -> Tuple[str, str]:
        read_date = format_iso_date(comparison.read_value)
        application_date = format_iso_date(comparison.application_value)
        if read_date == application_date:
            return CheckStatus.PASS.value, f"Both read {read_date}."
        detail = (
            f"{comparison.document_type_label} reads {read_date}. "
            f"Application reads {application_date or NOTHING_READ}."
        )
        return CheckStatus.FAIL.value, detail

    @classmethod
    def _compare_gender(cls, comparison: FieldComparisonDTO) -> Tuple[str, str]:
        read_gender = cls._normalise_word(comparison.read_value)
        application_gender = cls._normalise_word(comparison.application_value)
        if read_gender == application_gender:
            return CheckStatus.PASS.value, f"Both read {comparison.read_value}."
        return cls._disagrees(comparison)

    @classmethod
    def _compare_loose_text(cls, comparison: FieldComparisonDTO) -> Tuple[str, str]:
        """For values written to local convention: a survey, plot or village name.

        Punctuation and spacing carry no meaning here — '118/2' and '118 / 2' are the
        same survey number — so both sides are reduced before they are compared.
        """
        if cls._normalise_loose(comparison.read_value) == cls._normalise_loose(
            comparison.application_value
        ):
            return CheckStatus.PASS.value, f"Both read {comparison.read_value}."
        return cls._disagrees(comparison)

    @classmethod
    def _compare_extent(cls, comparison: FieldComparisonDTO) -> Tuple[str, str]:
        if ExtentTolerance.agree(
            extent=comparison.read_value,
            comparison_extent=comparison.application_value,
            tolerance=EXTENT_TOLERANCE_SQ_YARD,
        ):
            return (
                CheckStatus.PASS.value,
                f"Both read {ExtentTolerance.read_extent(comparison.read_value):g} "
                "sq. yd.",
            )
        return cls._disagrees(comparison)

    @classmethod
    def _disagrees(cls, comparison: FieldComparisonDTO) -> Tuple[str, str]:
        """Reports a difference at the severity this particular field warrants."""
        return (
            read_disagreement_status(comparison.application_field_key),
            cls._reads_sentence(comparison),
        )

    @classmethod
    def _compare_identifier(cls, comparison: FieldComparisonDTO) -> Tuple[str, str]:
        read_identifier = cls._normalise_identifier(comparison.read_value)
        application_identifier = cls._normalise_identifier(comparison.application_value)
        shown_read = cls._shown(comparison=comparison, identifier=read_identifier)
        shown_application = cls._shown(
            comparison=comparison, identifier=application_identifier
        )
        if read_identifier == application_identifier:
            return CheckStatus.PASS.value, f"Both read {shown_read}."
        detail = (
            f"{comparison.document_type_label} reads {shown_read}. "
            f"Application reads {shown_application or NOTHING_READ}."
        )
        return read_disagreement_status(comparison.application_field_key), detail

    @classmethod
    def _compare_address(cls, comparison: FieldComparisonDTO) -> Tuple[str, str]:
        overlap = AddressOverlap.calculate(
            address=comparison.read_value,
            comparison_address=comparison.application_value,
        )
        if overlap >= ADDRESS_OVERLAP_PASS_FLOOR:
            return CheckStatus.PASS.value, ADDRESS_AGREES_DETAIL
        # A warning, never a failure: an applicant who moved has not filed a false
        # document, and the officer is the one who can tell the difference.
        detail = (
            f"Address on the document differs from the application. "
            f"Document: {comparison.read_value}. "
            f"Application: {comparison.application_value or NOTHING_READ}. "
            f"{ADDRESS_ADVISORY}"
        )
        return CheckStatus.WARN.value, detail

    @staticmethod
    def _shown(comparison: FieldComparisonDTO, identifier: str) -> str:
        return IdentifierMask.apply(value=identifier, masked=comparison.masked)

    @staticmethod
    def _normalise_identifier(value: str) -> str:
        return "".join(str(value or "").split()).upper()

    @staticmethod
    def _normalise_word(value: str) -> str:
        return " ".join(str(value or "").lower().split())

    @staticmethod
    def _normalise_loose(value: str) -> str:
        lowered = str(value or "").lower()
        alphanumeric = _NON_ALPHANUMERIC.sub(" ", lowered)
        return " ".join(alphanumeric.split())

    @staticmethod
    def _reads_sentence(comparison: FieldComparisonDTO) -> str:
        return (
            f"{comparison.document_type_label} reads {comparison.read_value}. "
            f"Application reads {comparison.application_value or NOTHING_READ}."
        )

    @staticmethod
    def _build_check(
        comparison: FieldComparisonDTO, title: str, status: str, detail: str
    ) -> CheckDTO:
        check_key = CHECK_KEYS_BY_APPLICATION_FIELD[comparison.application_field_key]
        return CheckDTO(
            check_id=f"{comparison.document_id}:{check_key}",
            document_id=comparison.document_id,
            group=CheckGroup.RULE.value,
            title=title,
            status=status,
            detail=detail,
            field_key=comparison.field_key,
        )
