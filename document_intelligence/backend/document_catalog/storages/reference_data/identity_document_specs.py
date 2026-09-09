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

AADHAAR_SPEC = DocumentTypeDTO(
    document_type_id=DocumentTypeEnum.AADHAAR.value,
    label="Aadhaar",
    icon=DocumentIcon.IDENTITY.value,
    preview_layout=PreviewLayout.CARD.value,
    issuer_service_id=IssuerServiceEnum.UIDAI.value,
    implemented=True,
    field_specs=(
        FieldSpecDTO(
            key="name",
            label="Name",
            kind=FieldKind.TEXT.value,
            application_field_key=ApplicationFieldKey.APPLICANT_NAME.value,
        ),
        FieldSpecDTO(
            key="dob",
            label="Date of birth",
            kind=FieldKind.DATE.value,
            application_field_key=ApplicationFieldKey.DATE_OF_BIRTH.value,
        ),
        FieldSpecDTO(
            key="gender",
            label="Gender",
            kind=FieldKind.TEXT.value,
            application_field_key=ApplicationFieldKey.GENDER.value,
        ),
        FieldSpecDTO(
            key="aadhaarNo",
            label="Aadhaar number",
            kind=FieldKind.IDENTIFIER.value,
            application_field_key=ApplicationFieldKey.AADHAAR_NUMBER.value,
            masked=True,
        ),
        FieldSpecDTO(
            key="address",
            label="Address",
            kind=FieldKind.TEXT.value,
            application_field_key=ApplicationFieldKey.ADDRESS.value,
            comparison_rule=FieldComparisonRule.ADDRESS_OVERLAP.value,
        ),
    ),
    structure_specs=(
        StructureSpecDTO(key="photo", label="Photograph"),
        StructureSpecDTO(key="qr", label="QR code"),
        StructureSpecDTO(key="emblem", label="National emblem"),
    ),
)

PAN_SPEC = DocumentTypeDTO(
    document_type_id=DocumentTypeEnum.PAN.value,
    label="PAN",
    icon=DocumentIcon.IDENTITY.value,
    preview_layout=PreviewLayout.CARD.value,
    issuer_service_id=IssuerServiceEnum.ITD_PAN.value,
    implemented=True,
    field_specs=(
        FieldSpecDTO(
            key="name",
            label="Name",
            kind=FieldKind.TEXT.value,
            application_field_key=ApplicationFieldKey.APPLICANT_NAME.value,
        ),
        FieldSpecDTO(
            key="parentName",
            label="Father's name",
            kind=FieldKind.TEXT.value,
            application_field_key=ApplicationFieldKey.PARENT_NAME.value,
        ),
        FieldSpecDTO(
            key="dob",
            label="Date of birth",
            kind=FieldKind.DATE.value,
            application_field_key=ApplicationFieldKey.DATE_OF_BIRTH.value,
        ),
        FieldSpecDTO(
            key="pan",
            label="PAN",
            kind=FieldKind.IDENTIFIER.value,
            application_field_key=ApplicationFieldKey.PAN.value,
        ),
    ),
    structure_specs=(
        StructureSpecDTO(key="photo", label="Photograph"),
        StructureSpecDTO(key="signature", label="Signature"),
        StructureSpecDTO(key="hologram", label="Hologram"),
    ),
)

DRIVING_LICENCE_SPEC = DocumentTypeDTO(
    document_type_id=DocumentTypeEnum.DRIVING_LICENCE.value,
    label="Driving licence",
    icon=DocumentIcon.IDENTITY.value,
    preview_layout=PreviewLayout.CARD.value,
    issuer_service_id=IssuerServiceEnum.SARATHI.value,
    implemented=True,
    field_specs=(
        FieldSpecDTO(
            key="name",
            label="Name",
            kind=FieldKind.TEXT.value,
            application_field_key=ApplicationFieldKey.APPLICANT_NAME.value,
        ),
        FieldSpecDTO(
            key="dob",
            label="Date of birth",
            kind=FieldKind.DATE.value,
            application_field_key=ApplicationFieldKey.DATE_OF_BIRTH.value,
        ),
        FieldSpecDTO(key="dlNo", label="Licence number", kind=FieldKind.IDENTIFIER.value),
        FieldSpecDTO(
            key="validUpto",
            label="Valid until",
            kind=FieldKind.DATE.value,
            comparison_rule=FieldComparisonRule.VALIDITY_WINDOW.value,
        ),
        FieldSpecDTO(
            key="address",
            label="Address",
            kind=FieldKind.TEXT.value,
            application_field_key=ApplicationFieldKey.ADDRESS.value,
            comparison_rule=FieldComparisonRule.ADDRESS_OVERLAP.value,
        ),
        FieldSpecDTO(key="bloodGroup", label="Blood group", kind=FieldKind.TEXT.value),
    ),
    structure_specs=(
        StructureSpecDTO(key="photo", label="Photograph"),
        StructureSpecDTO(key="hologram", label="Hologram"),
    ),
)

UNKNOWN_SPEC = DocumentTypeDTO(
    document_type_id=DocumentTypeEnum.UNKNOWN.value,
    label="Unknown document",
    icon=DocumentIcon.FILE.value,
    preview_layout=PreviewLayout.GENERIC.value,
    issuer_service_id=None,
    implemented=False,
    field_specs=(FieldSpecDTO(key="title", label="Title", kind=FieldKind.TEXT.value),),
    structure_specs=(),
)

IDENTITY_DOCUMENT_SPECS = (AADHAAR_SPEC, PAN_SPEC, DRIVING_LICENCE_SPEC, UNKNOWN_SPEC)
