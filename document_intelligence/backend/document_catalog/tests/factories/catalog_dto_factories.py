import factory

from document_catalog.constants.enums import (
    ApplicationFieldGroup,
    DocumentIcon,
    FieldKind,
    PreviewLayout,
)
from document_catalog.dtos.catalog_dtos import (
    ApplicationDTO,
    ApplicationFieldSpecDTO,
    DocumentTypeDTO,
    FieldSpecDTO,
    FilenameKeywordRuleDTO,
    IssuerServiceDTO,
    StructureSpecDTO,
)


class FieldSpecDTOFactory(factory.Factory):
    class Meta:
        model = FieldSpecDTO

    key = factory.Sequence(lambda n: f"field_{n + 1}")
    label = factory.Sequence(lambda n: f"Field {n + 1}")
    kind = FieldKind.TEXT.value
    application_field_key = None
    masked = False
    comparison_rule = None


class StructureSpecDTOFactory(factory.Factory):
    class Meta:
        model = StructureSpecDTO

    key = factory.Sequence(lambda n: f"structure_{n + 1}")
    label = factory.Sequence(lambda n: f"Structure {n + 1}")


class DocumentTypeDTOFactory(factory.Factory):
    class Meta:
        model = DocumentTypeDTO

    document_type_id = factory.Sequence(lambda n: f"document_type_{n + 1}")
    label = factory.Sequence(lambda n: f"Document type {n + 1}")
    icon = DocumentIcon.IDENTITY.value
    preview_layout = PreviewLayout.CARD.value
    issuer_service_id = None
    implemented = False
    field_specs = ()
    structure_specs = ()


class IssuerServiceDTOFactory(factory.Factory):
    class Meta:
        model = IssuerServiceDTO

    issuer_service_id = factory.Sequence(lambda n: f"issuer_service_{n + 1}")
    name = factory.Sequence(lambda n: f"Issuer service {n + 1}")
    latency_ms = 900
    endpoint = "POST /verify"


class FilenameKeywordRuleDTOFactory(factory.Factory):
    class Meta:
        model = FilenameKeywordRuleDTO

    keyword = factory.Sequence(lambda n: f"keyword_{n + 1}")
    document_type_id = factory.Sequence(lambda n: f"document_type_{n + 1}")


class ApplicationFieldSpecDTOFactory(factory.Factory):
    class Meta:
        model = ApplicationFieldSpecDTO

    key = factory.Sequence(lambda n: f"application_field_{n + 1}")
    label = factory.Sequence(lambda n: f"Application field {n + 1}")
    kind = FieldKind.TEXT.value
    group = ApplicationFieldGroup.APPLICANT.value
    masked = False
    options = ()


class ApplicationDTOFactory(factory.Factory):
    class Meta:
        model = ApplicationDTO

    application_id = factory.Sequence(lambda n: f"BN/2026/{n + 1:04d}")
    status = "Under scrutiny"
    field_values = factory.Dict({"applicantName": "Test Applicant"})
