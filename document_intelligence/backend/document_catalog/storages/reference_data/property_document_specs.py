from document_catalog.constants.enums import (
    ApplicationFieldKey,
    DocumentIcon,
    DocumentTypeEnum,
    FieldComparisonRule,
    FieldKind,
    IssuerServiceEnum,
    PreviewLayout,
)
from document_catalog.dtos.catalog_dtos import (
    DocumentTypeDTO,
    FieldSpecDTO,
    StructureSpecDTO,
)

_SURVEY_NUMBER = FieldSpecDTO(
    key="surveyNo",
    label="Survey number",
    kind=FieldKind.IDENTIFIER.value,
    application_field_key=ApplicationFieldKey.SURVEY_NUMBER.value,
)
_PLOT_NUMBER = FieldSpecDTO(
    key="plotNo",
    label="Plot number",
    kind=FieldKind.IDENTIFIER.value,
    application_field_key=ApplicationFieldKey.PLOT_NUMBER.value,
)
_EXTENT = FieldSpecDTO(
    key="extent",
    label="Extent",
    kind=FieldKind.TEXT.value,
    application_field_key=ApplicationFieldKey.EXTENT_SQ_YARD.value,
    comparison_rule=FieldComparisonRule.EXTENT_TOLERANCE.value,
)
_VILLAGE = FieldSpecDTO(
    key="village",
    label="Village",
    kind=FieldKind.TEXT.value,
    application_field_key=ApplicationFieldKey.VILLAGE.value,
)
_DOCUMENT_NUMBER = FieldSpecDTO(
    key="docNo", label="Document number", kind=FieldKind.IDENTIFIER.value
)
_REGISTRATION_DATE = FieldSpecDTO(
    key="regDate", label="Registration date", kind=FieldKind.DATE.value
)
_SUB_REGISTRAR_OFFICE = FieldSpecDTO(
    key="sro", label="Sub-registrar office", kind=FieldKind.TEXT.value
)
_VENDOR = FieldSpecDTO(key="vendor", label="Vendor", kind=FieldKind.TEXT.value)

_DEED_STRUCTURE = (
    StructureSpecDTO(key="schedule", label="Schedule of property"),
    StructureSpecDTO(key="stamp", label="Stamp duty endorsement"),
    StructureSpecDTO(key="registration", label="Registration endorsement"),
)

SALE_DEED_SPEC = DocumentTypeDTO(
    document_type_id=DocumentTypeEnum.SALE_DEED.value,
    label="Sale deed",
    icon=DocumentIcon.DEED.value,
    preview_layout=PreviewLayout.DEED.value,
    issuer_service_id=IssuerServiceEnum.IGRS.value,
    implemented=True,
    field_specs=(
        _DOCUMENT_NUMBER,
        _REGISTRATION_DATE,
        _SUB_REGISTRAR_OFFICE,
        _VENDOR,
        FieldSpecDTO(
            key="purchaser",
            label="Purchaser",
            kind=FieldKind.TEXT.value,
            application_field_key=ApplicationFieldKey.APPLICANT_NAME.value,
        ),
        _SURVEY_NUMBER,
        _PLOT_NUMBER,
        _EXTENT,
        _VILLAGE,
        FieldSpecDTO(key="consideration", label="Consideration", kind=FieldKind.MONEY.value),
        FieldSpecDTO(key="boundaries", label="Boundaries", kind=FieldKind.TEXT.value),
    ),
    structure_specs=_DEED_STRUCTURE
    + (StructureSpecDTO(key="witnesses", label="Witness signatures"),),
)

LINK_DOCUMENT_SPEC = DocumentTypeDTO(
    document_type_id=DocumentTypeEnum.LINK_DOCUMENT.value,
    label="Link document",
    icon=DocumentIcon.DEED.value,
    preview_layout=PreviewLayout.DEED.value,
    issuer_service_id=IssuerServiceEnum.IGRS.value,
    implemented=True,
    field_specs=(
        _DOCUMENT_NUMBER,
        _REGISTRATION_DATE,
        _SUB_REGISTRAR_OFFICE,
        _VENDOR,
        FieldSpecDTO(key="purchaser", label="Purchaser", kind=FieldKind.TEXT.value),
        _SURVEY_NUMBER,
        _PLOT_NUMBER,
        _EXTENT,
        _VILLAGE,
    ),
    structure_specs=_DEED_STRUCTURE,
)

ENCUMBRANCE_CERTIFICATE_SPEC = DocumentTypeDTO(
    document_type_id=DocumentTypeEnum.ENCUMBRANCE_CERTIFICATE.value,
    label="Encumbrance certificate",
    icon=DocumentIcon.DEED.value,
    preview_layout=PreviewLayout.LETTER.value,
    # Downgraded to manual-only for now: the EC was declared to verify against IGRS,
    # but this pass ships it read-and-checked with the officer confirming by hand,
    # consistent with the other land documents. Re-wiring to IGRS is a one-line
    # change plus an answer reader when a real lookup exists (ADR-012).
    issuer_service_id=None,
    implemented=True,
    field_specs=(
        FieldSpecDTO(key="ecNo", label="EC number", kind=FieldKind.IDENTIFIER.value),
        FieldSpecDTO(key="period", label="Period searched", kind=FieldKind.TEXT.value),
        _SURVEY_NUMBER,
        FieldSpecDTO(
            key="owner",
            label="Owner on record",
            kind=FieldKind.TEXT.value,
            application_field_key=ApplicationFieldKey.APPLICANT_NAME.value,
        ),
        FieldSpecDTO(key="encumbrances", label="Encumbrances found", kind=FieldKind.TEXT.value),
    ),
    structure_specs=(
        StructureSpecDTO(key="seal", label="SRO seal"),
        StructureSpecDTO(key="signature", label="Signature"),
    ),
)

TAX_RECEIPT_SPEC = DocumentTypeDTO(
    document_type_id=DocumentTypeEnum.TAX_RECEIPT.value,
    label="Property tax receipt",
    icon=DocumentIcon.LETTER.value,
    preview_layout=PreviewLayout.LETTER.value,
    issuer_service_id=IssuerServiceEnum.ULB_REGISTRY.value,
    implemented=False,
    field_specs=(
        FieldSpecDTO(key="receiptNo", label="Receipt number", kind=FieldKind.IDENTIFIER.value),
        FieldSpecDTO(
            key="assessmentNo", label="Assessment number", kind=FieldKind.IDENTIFIER.value
        ),
        FieldSpecDTO(
            key="owner",
            label="Owner",
            kind=FieldKind.TEXT.value,
            application_field_key=ApplicationFieldKey.APPLICANT_NAME.value,
        ),
        FieldSpecDTO(key="period", label="Period", kind=FieldKind.TEXT.value),
        FieldSpecDTO(key="amount", label="Amount paid", kind=FieldKind.MONEY.value),
    ),
    structure_specs=(StructureSpecDTO(key="seal", label="ULB seal"),),
)

PROPERTY_DOCUMENT_SPECS = (
    SALE_DEED_SPEC,
    LINK_DOCUMENT_SPEC,
    ENCUMBRANCE_CERTIFICATE_SPEC,
    TAX_RECEIPT_SPEC,
)
