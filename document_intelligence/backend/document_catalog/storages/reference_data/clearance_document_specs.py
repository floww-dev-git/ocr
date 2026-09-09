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
_APPLICANT = FieldSpecDTO(
    key="applicant",
    label="Applicant",
    kind=FieldKind.TEXT.value,
    application_field_key=ApplicationFieldKey.APPLICANT_NAME.value,
)
_ISSUED_BY = FieldSpecDTO(key="issuedBy", label="Issued by", kind=FieldKind.TEXT.value)
_ISSUE_DATE = FieldSpecDTO(key="issueDate", label="Issue date", kind=FieldKind.DATE.value)
_VALID_UPTO = FieldSpecDTO(
    key="validUpto",
    label="Valid until",
    kind=FieldKind.DATE.value,
    comparison_rule=FieldComparisonRule.VALIDITY_WINDOW.value,
)

_AUTHORITY_STRUCTURE = (
    StructureSpecDTO(key="seal", label="Office seal"),
    StructureSpecDTO(key="signature", label="Signature of authority"),
    StructureSpecDTO(key="conditions", label="Conditions annexure"),
)

BUILDING_PERMIT_SPEC = DocumentTypeDTO(
    document_type_id=DocumentTypeEnum.BUILDING_PERMIT.value,
    label="Earlier building permission",
    icon=DocumentIcon.LETTER.value,
    preview_layout=PreviewLayout.LETTER.value,
    issuer_service_id=IssuerServiceEnum.ULB_REGISTRY.value,
    implemented=False,
    field_specs=(
        FieldSpecDTO(key="permitNo", label="Permit number", kind=FieldKind.IDENTIFIER.value),
        _ISSUED_BY,
        _ISSUE_DATE,
        _VALID_UPTO,
        _APPLICANT,
        _SURVEY_NUMBER,
        FieldSpecDTO(key="permittedUse", label="Permitted use", kind=FieldKind.TEXT.value),
        FieldSpecDTO(key="permittedFloors", label="Permitted floors", kind=FieldKind.TEXT.value),
    ),
    structure_specs=_AUTHORITY_STRUCTURE,
)

FIRE_NOC_SPEC = DocumentTypeDTO(
    document_type_id=DocumentTypeEnum.FIRE_NOC.value,
    label="Fire NOC",
    icon=DocumentIcon.LETTER.value,
    preview_layout=PreviewLayout.LETTER.value,
    issuer_service_id=IssuerServiceEnum.FIRE_REGISTRY.value,
    implemented=False,
    field_specs=(
        FieldSpecDTO(key="nocNo", label="NOC number", kind=FieldKind.IDENTIFIER.value),
        _ISSUED_BY,
        _ISSUE_DATE,
        _VALID_UPTO,
        _APPLICANT,
        _SURVEY_NUMBER,
        FieldSpecDTO(
            key="heightApprovedM",
            label="Height approved (m)",
            kind=FieldKind.NUMBER.value,
            comparison_rule=FieldComparisonRule.HEIGHT_AT_LEAST.value,
        ),
        FieldSpecDTO(
            key="floorsApproved",
            label="Floors approved",
            kind=FieldKind.TEXT.value,
            application_field_key=ApplicationFieldKey.FLOORS.value,
        ),
    ),
    structure_specs=(
        StructureSpecDTO(key="seal", label="Department seal"),
        StructureSpecDTO(key="signature", label="Signature of authority"),
        StructureSpecDTO(key="conditions", label="Conditions annexure"),
    ),
)

AAI_NOC_SPEC = DocumentTypeDTO(
    document_type_id=DocumentTypeEnum.AAI_NOC.value,
    label="AAI NOC",
    icon=DocumentIcon.LETTER.value,
    preview_layout=PreviewLayout.LETTER.value,
    issuer_service_id=IssuerServiceEnum.AAI_NOCAS.value,
    implemented=False,
    field_specs=(
        FieldSpecDTO(key="nocId", label="NOC id", kind=FieldKind.IDENTIFIER.value),
        _ISSUE_DATE,
        _VALID_UPTO,
        _APPLICANT,
        _SURVEY_NUMBER,
        FieldSpecDTO(key="siteCoordinates", label="Site coordinates", kind=FieldKind.TEXT.value),
        FieldSpecDTO(
            key="permissibleHeightM",
            label="Permissible height (m)",
            kind=FieldKind.NUMBER.value,
            comparison_rule=FieldComparisonRule.HEIGHT_AT_LEAST.value,
        ),
    ),
    structure_specs=(
        StructureSpecDTO(key="qr", label="Verification QR"),
        StructureSpecDTO(key="signature", label="Digital signature"),
    ),
)

IRRIGATION_NOC_SPEC = DocumentTypeDTO(
    document_type_id=DocumentTypeEnum.IRRIGATION_NOC.value,
    label="Irrigation NOC",
    icon=DocumentIcon.LETTER.value,
    preview_layout=PreviewLayout.LETTER.value,
    # The Irrigation and CAD Department publishes no verification interface, so this
    # is the one implemented type with nothing to ask. Verification says so as a
    # check of its own and leaves the confirmation to the officer.
    issuer_service_id=None,
    implemented=True,
    field_specs=(
        FieldSpecDTO(key="nocNo", label="NOC number", kind=FieldKind.IDENTIFIER.value),
        _ISSUED_BY,
        _ISSUE_DATE,
        _VALID_UPTO,
        _APPLICANT,
        _SURVEY_NUMBER,
        FieldSpecDTO(key="bufferCondition", label="Buffer condition", kind=FieldKind.TEXT.value),
    ),
    structure_specs=(
        StructureSpecDTO(key="seal", label="Department seal"),
        StructureSpecDTO(key="signature", label="Signature of authority"),
    ),
)

CLEARANCE_DOCUMENT_SPECS = (
    BUILDING_PERMIT_SPEC,
    FIRE_NOC_SPEC,
    AAI_NOC_SPEC,
    IRRIGATION_NOC_SPEC,
)
