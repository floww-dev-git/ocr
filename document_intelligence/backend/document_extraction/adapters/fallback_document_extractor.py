"""A primary extractor with a safety net under it.

Real extraction at demo time is a live model call: a dropped network, a spent
quota, or a missing key would otherwise stop the run cold on stage. This wraps the
primary (Gemini) and, only when the primary cannot even attempt the read — an
extraction failure or a missing credential — falls through to the mock reader so the
scenario still plays. A genuine "this scan is unreadable" from the model is NOT one
of those cases and is left to surface: the fallback catches infrastructure failing,
not the document being bad.

Both `classify_document` and `extract_document_record` fall back together, because a
classify that fell to mock and an extract that reached the real model would read the
document with two different minds.
"""
from typing import Optional

from document_extraction.adapters.document_extractor_interface import (
    DocumentExtractorInterface,
)
from document_extraction.dtos.document_record_dtos import DocumentRecordDTO
from document_extraction.dtos.extraction_dtos import (
    DocumentClassificationDTO,
    ExtractDocumentRequestDTO,
)
from document_extraction.exceptions.extraction_exceptions import (
    ExtractionCredentialMissing,
    ExtractionFailed,
)

# The failures that mean "the primary could not run" — worth falling back for. A
# DocumentReadNotRegistered or a genuine unreadable-scan is deliberately not here.
_FALLBACK_ON = (ExtractionFailed, ExtractionCredentialMissing)


class FallbackDocumentExtractor(DocumentExtractorInterface):
    def __init__(
        self,
        primary: DocumentExtractorInterface,
        fallback: DocumentExtractorInterface,
        on_fallback: Optional[callable] = None,
    ):
        self.primary = primary
        self.fallback = fallback
        # An optional hook so a caller can record that the safety net was used
        # (surfaced to the UI as an honesty flag). Kept side-effect free by default.
        self.on_fallback = on_fallback

    def classify_document(
        self, request: ExtractDocumentRequestDTO
    ) -> DocumentClassificationDTO:
        try:
            return self.primary.classify_document(request=request)
        except _FALLBACK_ON:
            self._note_fallback()
            return self.fallback.classify_document(request=request)

    def extract_document_record(
        self, request: ExtractDocumentRequestDTO
    ) -> DocumentRecordDTO:
        try:
            return self.primary.extract_document_record(request=request)
        except _FALLBACK_ON:
            self._note_fallback()
            return self.fallback.extract_document_record(request=request)

    def _note_fallback(self) -> None:
        if self.on_fallback is not None:
            self.on_fallback()
