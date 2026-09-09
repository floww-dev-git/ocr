import enum
from typing import Mapping

from document_scrutiny.constants.enums import CheckStatus


class ComparableApplicationField(enum.Enum):
    APPLICANT_NAME = "applicantName"
    PARENT_NAME = "parentName"
    DATE_OF_BIRTH = "dob"
    GENDER = "gender"
    AADHAAR_NUMBER = "aadhaarNo"
    PAN = "pan"
    ADDRESS = "address"
    SURVEY_NUMBER = "surveyNo"
    PLOT_NUMBER = "plotNo"
    VILLAGE = "village"
    EXTENT_SQ_YARD = "extentSqYd"


# The check key is half of a check's identity (`<document_id>:<check_key>`), so these
# are effectively permanent: changing one orphans the officer's acknowledgement of
# every check already carrying the old id. Each field gets its own key rather than a
# shared "id", so a document holding both a PAN and an Aadhaar cannot collide.
CHECK_KEYS_BY_APPLICATION_FIELD = {
    ComparableApplicationField.APPLICANT_NAME.value: "name",
    ComparableApplicationField.PARENT_NAME.value: "parent",
    ComparableApplicationField.DATE_OF_BIRTH.value: "dob",
    ComparableApplicationField.GENDER.value: "gender",
    ComparableApplicationField.AADHAAR_NUMBER.value: "aadhaar",
    ComparableApplicationField.PAN.value: "pan",
    ComparableApplicationField.ADDRESS.value: "address",
    ComparableApplicationField.SURVEY_NUMBER.value: "survey",
    ComparableApplicationField.PLOT_NUMBER.value: "plot",
    ComparableApplicationField.VILLAGE.value: "village",
    ComparableApplicationField.EXTENT_SQ_YARD.value: "extent",
}

# How seriously a disagreement on each field is taken. A failure says the document
# and the application cannot both be right; a warning says they differ for reasons
# an officer can often explain. The survey number identifies the parcel itself, so a
# difference there is a failure. A plot number, a village name and an extent are
# written to local convention and get renumbered, so they are warnings. Anything not
# named here fails, which is the safer default for a field nobody has thought about.
DISAGREEMENT_STATUS_BY_APPLICATION_FIELD: Mapping[str, str] = {
    ComparableApplicationField.PLOT_NUMBER.value: CheckStatus.WARN.value,
    ComparableApplicationField.VILLAGE.value: CheckStatus.WARN.value,
    ComparableApplicationField.EXTENT_SQ_YARD.value: CheckStatus.WARN.value,
    ComparableApplicationField.ADDRESS.value: CheckStatus.WARN.value,
}


def read_disagreement_status(application_field_key: str) -> str:
    return DISAGREEMENT_STATUS_BY_APPLICATION_FIELD.get(
        application_field_key, CheckStatus.FAIL.value
    )
