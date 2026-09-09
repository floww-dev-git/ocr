"""Print the PAN check table for every seeded application.

Runs the real check engine over the canned sample reads, with no server, no HTTP and
no API key. Forces EXTRACTION_MODE=mock because it ships no document files to read —
real extraction is exercised through the running server instead.

    uv run python -m scripts.print_check_table
"""
import dataclasses
import os
import sys

import django
from django.conf import settings

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
os.environ["EXTRACTION_MODE"] = "mock"
django.setup()

from document_catalog.app_interfaces.catalog_service_interface import (  # noqa: E402
    CatalogServiceInterface,
)
from document_catalog.storages.reference_data.application_specs import (  # noqa: E402
    APPLICATION_SPECS,
)
from document_extraction.app_interfaces.extraction_service_interface import (  # noqa: E402
    ExtractionServiceInterface,
)
from document_extraction.constants.extraction_constants import (  # noqa: E402
    DocumentSource,
)
from document_extraction.dtos.extraction_dtos import (  # noqa: E402
    ExtractDocumentRequestDTO,
)
from document_scrutiny.domain.document_verdict import DocumentVerdict  # noqa: E402
from document_scrutiny.domain.scrutiny_summary import ScrutinySummary  # noqa: E402
from document_scrutiny.dtos.document_dtos import (  # noqa: E402
    DocumentStateDTO,
    FieldValueDTO,
)
from document_scrutiny.dtos.run_checks_dtos import (  # noqa: E402
    RunDocumentChecksRequestDTO,
)
from document_scrutiny.interactors.run_document_checks_interactor import (  # noqa: E402
    RunDocumentChecksInteractor,
)

STATUS_LABELS = {"pass": "PASS", "warn": "WARN", "fail": "FAIL", "unavailable": "N/A "}
DOCUMENT_ID = "document_1"


def _build_document(application_id: str) -> DocumentStateDTO:
    extraction_service = ExtractionServiceInterface()
    catalog_service = CatalogServiceInterface()
    request = ExtractDocumentRequestDTO(
        filename="pan_card.pdf",
        application_id=application_id,
        source=DocumentSource.SAMPLE.value,
    )
    classification = extraction_service.classify_document(request=request)
    record = extraction_service.extract_document_record(
        request=dataclasses.replace(
            request, document_type_id=classification.document_type_id
        )
    )
    document_type = catalog_service.get_document_type(
        document_type_id=classification.document_type_id
    )
    application = catalog_service.get_application(application_id=application_id)

    field_values = tuple(
        FieldValueDTO(key=read.key, value=read.value, confidence=read.confidence)
        for read in record.field_reads
    )
    checks = RunDocumentChecksInteractor().run_checks(
        request=RunDocumentChecksRequestDTO(
            document_id=DOCUMENT_ID,
            document_type=document_type,
            application=application,
            scrutiny_today=settings.SCRUTINY_TODAY,
            field_values=field_values,
            structure_findings=record.structure_findings,
        )
    )
    return DocumentStateDTO(
        document_id=DOCUMENT_ID,
        filename=request.filename,
        file_format="PDF",
        file_size_bytes=0,
        document_type_id=classification.document_type_id,
        document_type_label=classification.document_type_label,
        type_confidence=classification.type_confidence,
        implemented=classification.implemented,
        stage="done",
        status="",
        confirmed=False,
        page_count=record.page_count,
        field_values=field_values,
        structure_findings=record.structure_findings,
        checks=tuple(checks),
    )


def print_check_table() -> None:
    for application in APPLICATION_SPECS:
        document = _build_document(application.application_id)
        summary = ScrutinySummary.summarise(documents=(document,))
        verdict = DocumentVerdict.derive(stage=document.stage, checks=document.checks)

        applicant = application.field_values["applicantName"]
        print(f"\n{application.application_id}   {applicant}")
        for field_value in document.field_values:
            print(f"    read {field_value.key:12} {field_value.value:30} ({field_value.confidence})")
        for check in document.checks:
            label = STATUS_LABELS.get(check.status, check.status)
            print(f"  [{label}] {check.title:42} {check.detail}")
        print(f"  -> document: {verdict}   thread: {summary.thread_status}")
        counts = {name: total for name, total in summary.status_counts.items() if total}
        print(f"     counts: {counts}")
        for open_item in summary.open_items:
            print(f"     open: {open_item.text}")


if __name__ == "__main__":
    print_check_table()
    sys.exit(0)
