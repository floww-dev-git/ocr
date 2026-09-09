from typing import Callable, Dict

from django.conf import settings

from document_extraction.adapters.document_extractor_interface import (
    DocumentExtractorInterface,
)
from document_extraction.constants.extraction_constants import ExtractionMode
from document_extraction.exceptions.extraction_exceptions import (
    UnsupportedExtractionMode,
)


def _build_mock_extractor() -> DocumentExtractorInterface:
    from document_extraction.adapters.mock_document_extractor import (
        MockDocumentExtractor,
    )

    return MockDocumentExtractor()


def _build_gemini_extractor() -> DocumentExtractorInterface:
    from document_extraction.adapters.gemini_document_extractor import (
        GeminiDocumentExtractor,
    )

    gemini = GeminiDocumentExtractor()
    if not getattr(settings, "EXTRACTION_FALLBACK", False):
        return gemini
    # The demo runs on real Gemini but must not hard-fail on a dropped network or a
    # spent key, so the mock reader sits under it as a safety net (ADR-013).
    from document_extraction.adapters.fallback_document_extractor import (
        FallbackDocumentExtractor,
    )

    return FallbackDocumentExtractor(primary=gemini, fallback=_build_mock_extractor())


_BUILDERS_BY_MODE: Dict[str, Callable[[], DocumentExtractorInterface]] = {
    ExtractionMode.MOCK.value: _build_mock_extractor,
    ExtractionMode.GEMINI.value: _build_gemini_extractor,
}


def get_document_extractor() -> DocumentExtractorInterface:
    extraction_mode = getattr(settings, "EXTRACTION_MODE", ExtractionMode.MOCK.value)
    builder = _BUILDERS_BY_MODE.get(extraction_mode)
    if builder is None:
        raise UnsupportedExtractionMode(extraction_mode=extraction_mode)
    return builder()
