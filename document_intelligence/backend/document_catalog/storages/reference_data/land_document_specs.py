"""Revenue and land-record documents, all manual-only.

These are the parcel's revenue-side paper — conversion orders, market-value
certificates, the pattadar pass book and an occupancy rights certificate — as
distinct from the registration-side deeds in `property_document_specs.py`. None of
their issuing departments (RDO, the sub-registrar's valuation cell, the Revenue
Department's Dharani system) publishes a verification interface in this build, so
every one carries `issuer_service_id=None` and settles through
`ManualVerificationCheck` (see ADR-011, ADR-012).

The field lists for the four new types are inferred from the general Telangana
forms, not from real specimens (ADR-012). They are internally consistent and their
keys match the read modules and the canned sample reads, but a real integration is
where the exact fields get confirmed or corrected.
"""
from document_catalog.constants.enums import (
    ApplicationFieldKey,
    DocumentIcon,
    DocumentTypeEnum,
    FieldComparisonRule,
    FieldKind,
    PreviewLayout,
)
from document_catalog.dtos.catalog_dtos import (
    DocumentTypeDTO,
    FieldSpecDTO,
    StructureSpecDTO,
)

# Shared field specs, so every land document that names the parcel compares it the
# same way the deeds do. Reused verbatim from the domain the deeds already model.
_SURVEY_NUMBER = FieldSpecDTO(
    key="surveyNo",
    label="Survey number",
    kind=FieldKind.IDENTIFIER.value,
    application_field_key=ApplicationFieldKey.SURVEY_NUMBER.value,
)
_VILLAGE = FieldSpecDTO(
    key="village",
    label="Village",
    kind=FieldKind.TEXT.value,
    application_field_key=ApplicationFieldKey.VILLAGE.value,
)
_EXTENT = FieldSpecDTO(
    key="extent",
    label="Extent",
    kind=FieldKind.TEXT.value,
    application_field_key=ApplicationFieldKey.EXTENT_SQ_YARD.value,
    comparison_rule=FieldComparisonRule.EXTENT_TOLERANCE.value,
)
_ISSUE_DATE = FieldSpecDTO(key="issueDate", label="Issue date", kind=FieldKind.DATE.value)
_ISSUED_BY = FieldSpecDTO(key="issuedBy", label="Issued by", kind=FieldKind.TEXT.value)

_SEAL_AND_SIGNATURE = (
    StructureSpecDTO(key="seal", label="Office seal"),
    StructureSpecDTO(key="signature", label="Signature of authority"),
)

CONVERSION_CERT_SPEC = DocumentTypeDTO(
    document_type_id=DocumentTypeEnum.CONVERSION_CERT.value,
    label="Land conversion certificate",
    icon=DocumentIcon.LETTER.value,
    preview_layout=PreviewLayout.LETTER.value,
    # Issued by the RDO under the Telangana NALA Act, 2006; no verification service.
    issuer_service_id=None,
    implemented=True,
    field_specs=(
        FieldSpecDTO(
            key="conversionOrderNo",
            label="Conversion order number",
            kind=FieldKind.IDENTIFIER.value,
        ),
        _ISSUED_BY,
        _ISSUE_DATE,
        FieldSpecDTO(
            key="applicant",
            label="Applicant",
            kind=FieldKind.TEXT.value,
            application_field_key=ApplicationFieldKey.APPLICANT_NAME.value,
        ),
        _SURVEY_NUMBER,
        _VILLAGE,
        _EXTENT,
        FieldSpecDTO(
            key="convertedUse", label="Converted use", kind=FieldKind.TEXT.value
        ),
        FieldSpecDTO(
            key="nalaAssessment",
            label="NALA assessment paid",
            kind=FieldKind.MONEY.value,
        ),
    ),
    structure_specs=_SEAL_AND_SIGNATURE,
)

MARKET_VALUE_CERT_SPEC = DocumentTypeDTO(
    document_type_id=DocumentTypeEnum.MARKET_VALUE_CERT.value,
    label="Market value certificate",
    icon=DocumentIcon.LETTER.value,
    preview_layout=PreviewLayout.LETTER.value,
    # Issued by the concerned sub-registrar office; the valuation cell exposes no
    # lookup, so this settles by the officer's hand.
    issuer_service_id=None,
    implemented=True,
    field_specs=(
        FieldSpecDTO(
            key="certificateNo",
            label="Certificate number",
            kind=FieldKind.IDENTIFIER.value,
        ),
        FieldSpecDTO(key="sro", label="Sub-registrar office", kind=FieldKind.TEXT.value),
        _ISSUE_DATE,
        _SURVEY_NUMBER,
        _VILLAGE,
        # The rate itself has no counterpart on the application form, so it is read
        # and shown but never compared.
        FieldSpecDTO(
            key="marketValuePerSqYd",
            label="Market value per sq. yd",
            kind=FieldKind.MONEY.value,
        ),
        FieldSpecDTO(
            key="valuationAsOn", label="Valuation as on", kind=FieldKind.DATE.value
        ),
    ),
    structure_specs=_SEAL_AND_SIGNATURE,
)

PATTADAR_PASSBOOK_SPEC = DocumentTypeDTO(
    document_type_id=DocumentTypeEnum.PATTADAR_PASSBOOK.value,
    label="Pattadar pass book / Title deed",
    icon=DocumentIcon.DEED.value,
    preview_layout=PreviewLayout.DEED.value,
    # A Revenue Department record (Dharani). No public verification interface here.
    issuer_service_id=None,
    implemented=True,
    field_specs=(
        FieldSpecDTO(
            key="passbookNo",
            label="Pass book number",
            kind=FieldKind.IDENTIFIER.value,
        ),
        FieldSpecDTO(
            key="pattadar",
            label="Pattadar",
            kind=FieldKind.TEXT.value,
            application_field_key=ApplicationFieldKey.APPLICANT_NAME.value,
        ),
        FieldSpecDTO(
            key="khataNo", label="Khata number", kind=FieldKind.IDENTIFIER.value
        ),
        _SURVEY_NUMBER,
        _VILLAGE,
        _EXTENT,
        FieldSpecDTO(key="landClassification", label="Land classification", kind=FieldKind.TEXT.value),
        _ISSUE_DATE,
    ),
    structure_specs=(
        StructureSpecDTO(key="photo", label="Pattadar photograph"),
        StructureSpecDTO(key="seal", label="Revenue seal"),
        StructureSpecDTO(key="signature", label="Tahsildar signature"),
    ),
)

ORC_SPEC = DocumentTypeDTO(
    document_type_id=DocumentTypeEnum.ORC.value,
    label="Occupancy rights certificate",
    icon=DocumentIcon.LETTER.value,
    preview_layout=PreviewLayout.LETTER.value,
    # Issued by the RDO for Inam lands. No verification interface.
    issuer_service_id=None,
    implemented=True,
    field_specs=(
        FieldSpecDTO(key="orcNo", label="ORC number", kind=FieldKind.IDENTIFIER.value),
        _ISSUED_BY,
        _ISSUE_DATE,
        FieldSpecDTO(
            key="occupant",
            label="Occupant",
            kind=FieldKind.TEXT.value,
            application_field_key=ApplicationFieldKey.APPLICANT_NAME.value,
        ),
        _SURVEY_NUMBER,
        _VILLAGE,
        # Extent is read for the record but not compared: an ORC establishes who
        # occupies the Inam land, and the extent decision was survey + village +
        # occupant only.
        FieldSpecDTO(key="extent", label="Extent", kind=FieldKind.TEXT.value),
        FieldSpecDTO(key="inamCategory", label="Inam category", kind=FieldKind.TEXT.value),
    ),
    structure_specs=_SEAL_AND_SIGNATURE,
)

LAND_DOCUMENT_SPECS = (
    CONVERSION_CERT_SPEC,
    MARKET_VALUE_CERT_SPEC,
    PATTADAR_PASSBOOK_SPEC,
    ORC_SPEC,
)
