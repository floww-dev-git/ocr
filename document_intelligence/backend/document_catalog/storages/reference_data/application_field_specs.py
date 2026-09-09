from typing import Tuple

from document_catalog.constants.enums import (
    ApplicationFieldGroup,
    ApplicationFieldKey,
    FieldKind,
)
from document_catalog.dtos.catalog_dtos import ApplicationFieldSpecDTO

_APPLICANT = ApplicationFieldGroup.APPLICANT.value
_PLOT = ApplicationFieldGroup.PLOT.value
_PROPOSAL = ApplicationFieldGroup.PROPOSAL.value

APPLICATION_FIELD_SPECS: Tuple[ApplicationFieldSpecDTO, ...] = (
    ApplicationFieldSpecDTO(
        key=ApplicationFieldKey.APPLICANT_NAME.value,
        label="Applicant",
        kind=FieldKind.TEXT.value,
        group=_APPLICANT,
    ),
    ApplicationFieldSpecDTO(
        key=ApplicationFieldKey.PARENT_NAME.value,
        label="Father or husband",
        kind=FieldKind.TEXT.value,
        group=_APPLICANT,
    ),
    ApplicationFieldSpecDTO(
        key=ApplicationFieldKey.DATE_OF_BIRTH.value,
        label="Date of birth",
        kind=FieldKind.DATE.value,
        group=_APPLICANT,
    ),
    ApplicationFieldSpecDTO(
        key=ApplicationFieldKey.GENDER.value,
        label="Gender",
        kind=FieldKind.SELECT.value,
        group=_APPLICANT,
        options=("Male", "Female", "Other"),
    ),
    ApplicationFieldSpecDTO(
        key=ApplicationFieldKey.AADHAAR_NUMBER.value,
        label="Aadhaar",
        kind=FieldKind.IDENTIFIER.value,
        group=_APPLICANT,
        masked=True,
    ),
    ApplicationFieldSpecDTO(
        key=ApplicationFieldKey.PAN.value,
        label="PAN",
        kind=FieldKind.IDENTIFIER.value,
        group=_APPLICANT,
    ),
    ApplicationFieldSpecDTO(
        key=ApplicationFieldKey.MOBILE.value,
        label="Mobile",
        kind=FieldKind.IDENTIFIER.value,
        group=_APPLICANT,
    ),
    ApplicationFieldSpecDTO(
        key=ApplicationFieldKey.ADDRESS.value,
        label="Address",
        kind=FieldKind.TEXT.value,
        group=_APPLICANT,
    ),
    ApplicationFieldSpecDTO(
        key=ApplicationFieldKey.PLOT_NUMBER.value,
        label="Plot number",
        kind=FieldKind.IDENTIFIER.value,
        group=_PLOT,
    ),
    ApplicationFieldSpecDTO(
        key=ApplicationFieldKey.SURVEY_NUMBER.value,
        label="Survey number",
        kind=FieldKind.IDENTIFIER.value,
        group=_PLOT,
    ),
    ApplicationFieldSpecDTO(
        key=ApplicationFieldKey.VILLAGE.value,
        label="Village",
        kind=FieldKind.TEXT.value,
        group=_PLOT,
    ),
    ApplicationFieldSpecDTO(
        key=ApplicationFieldKey.MANDAL.value,
        label="Mandal",
        kind=FieldKind.TEXT.value,
        group=_PLOT,
    ),
    ApplicationFieldSpecDTO(
        key=ApplicationFieldKey.DISTRICT.value,
        label="District",
        kind=FieldKind.TEXT.value,
        group=_PLOT,
    ),
    ApplicationFieldSpecDTO(
        key=ApplicationFieldKey.URBAN_LOCAL_BODY.value,
        label="Urban local body",
        kind=FieldKind.TEXT.value,
        group=_PLOT,
    ),
    ApplicationFieldSpecDTO(
        key=ApplicationFieldKey.EXTENT_SQ_YARD.value,
        label="Extent (sq. yd)",
        kind=FieldKind.NUMBER.value,
        group=_PLOT,
    ),
    ApplicationFieldSpecDTO(
        key=ApplicationFieldKey.PROPOSED_USE.value,
        label="Proposed use",
        kind=FieldKind.TEXT.value,
        group=_PROPOSAL,
    ),
    ApplicationFieldSpecDTO(
        key=ApplicationFieldKey.FLOORS.value,
        label="Floors",
        kind=FieldKind.TEXT.value,
        group=_PROPOSAL,
    ),
    ApplicationFieldSpecDTO(
        key=ApplicationFieldKey.HEIGHT_METRES.value,
        label="Height (m)",
        kind=FieldKind.NUMBER.value,
        group=_PROPOSAL,
    ),
    ApplicationFieldSpecDTO(
        key=ApplicationFieldKey.NEAR_WATER_BODY.value,
        label="Near water body",
        kind=FieldKind.SELECT.value,
        group=_PROPOSAL,
        options=("Yes", "No"),
    ),
    ApplicationFieldSpecDTO(
        key=ApplicationFieldKey.ROAD_WIDTH_METRES.value,
        label="Road width (m)",
        kind=FieldKind.NUMBER.value,
        group=_PROPOSAL,
    ),
)
