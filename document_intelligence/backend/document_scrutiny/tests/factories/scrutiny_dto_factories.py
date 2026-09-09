import factory

from document_scrutiny.constants.enums import (
    CheckGroup,
    CheckStatus,
    DocumentStage,
    DocumentStatus,
)
from document_scrutiny.dtos.check_dtos import CheckDTO, IssuerCallDTO
from document_scrutiny.dtos.document_dtos import DocumentStateDTO, FieldValueDTO


class FieldValueDTOFactory(factory.Factory):
    class Meta:
        model = FieldValueDTO

    key = factory.Sequence(lambda n: f"field_{n + 1}")
    value = factory.Sequence(lambda n: f"value {n + 1}")
    confidence = 0.9
    edited = False
    confirmed = False


class IssuerCallDTOFactory(factory.Factory):
    class Meta:
        model = IssuerCallDTO

    issuer_service_id = "itd_pan"
    name = "Income Tax PAN verification"
    endpoint = "POST /pan/verify"
    latency_ms = 900
    request_payload = factory.Dict({"pan": "DQRPK4831L"})
    response_payload = factory.Dict({"status": "VALID"})


class CheckDTOFactory(factory.Factory):
    class Meta:
        model = CheckDTO

    check_id = factory.Sequence(lambda n: f"document_1:check_{n + 1}")
    document_id = "document_1"
    group = CheckGroup.RULE.value
    title = factory.Sequence(lambda n: f"Check {n + 1}")
    status = CheckStatus.PASS.value
    detail = "Everything agrees."
    field_key = None
    acknowledged = False
    manual = False
    requested = False
    issuer_call = None


class DocumentStateDTOFactory(factory.Factory):
    class Meta:
        model = DocumentStateDTO

    document_id = factory.Sequence(lambda n: f"document_{n + 1}")
    filename = factory.Sequence(lambda n: f"pan_card_{n + 1}.pdf")
    file_format = "PDF"
    file_size_bytes = 188000
    document_type_id = "pan"
    document_type_label = "PAN"
    type_confidence = 0.99
    implemented = True
    stage = DocumentStage.DONE.value
    status = DocumentStatus.VERIFIED.value
    confirmed = False
    page_count = 1
    field_values = ()
    structure_findings = factory.Dict({})
    checks = ()
    page_image_urls = ()
