from typing import Optional, Tuple

from document_catalog.dtos.catalog_dtos import DocumentTypeDTO
from document_extraction.adapters.bundle_sample_reads import (
    BundleSampleRead,
    BundleSegmentRead,
    get_bundle_sample_read,
    get_bundle_segment_read,
)
from document_extraction.adapters.document_extractor_interface import (
    DocumentExtractorInterface,
)
from document_extraction.adapters.sample_reads import (
    DocumentSampleRead,
    get_sample_read,
)
from document_extraction.adapters.service_adapter import get_service_adapter
from document_extraction.constants.extraction_constants import (
    KEYWORD_MATCH_TYPE_CONFIDENCE,
    UNRECOGNISED_TYPE_CONFIDENCE,
    DocumentSource,
)
from document_extraction.domain.page_segments import PageSegments
from document_extraction.domain.read_confidence import ReadConfidence
from document_extraction.dtos.document_record_dtos import (
    DocumentRecordDTO,
    FieldBoxDTO,
    FieldReadDTO,
)
from document_extraction.dtos.extraction_dtos import (
    DocumentClassificationDTO,
    DocumentSegmentDTO,
    ExtractDocumentRequestDTO,
)
from document_extraction.exceptions.extraction_exceptions import (
    NoSampleReadForApplication,
)

UNRECOGNISED_DOCUMENT_TYPE_ID = "unknown"
DEFAULT_PAGE_COUNT = 1


class MockDocumentExtractor(DocumentExtractorInterface):
    """Deterministic canned reads, so the demo runs offline with no API key.

    Classification is by filename keyword, which is also how the officer's own
    naming decides which sample comes back. A file named as one of the shipped deed
    bundles is recognised by its whole name instead, because a bundle is a specific
    file rather than a kind of file.
    """

    @property
    def catalog_service(self):
        return get_service_adapter().catalog_service

    def classify_document(
        self, request: ExtractDocumentRequestDTO
    ) -> DocumentClassificationDTO:
        segment = get_bundle_segment_read(
            filename=request.filename, page_start=request.page_start
        )
        if segment is not None:
            return self._classify_segment(segment=segment)
        bundle = get_bundle_sample_read(filename=request.filename)
        if bundle is not None and not request.is_page_slice:
            return self._classify_bundle(bundle=bundle)
        return self._classify_by_sample(request=request)

    def extract_document_record(
        self, request: ExtractDocumentRequestDTO
    ) -> DocumentRecordDTO:
        sample_read = self._read_sample(request=request)
        if sample_read is None:
            raise NoSampleReadForApplication(
                application_id=request.application_id,
                document_type_id=str(request.document_type_id or ""),
            )

        field_reads = self._build_field_reads(
            sample_read=sample_read, source=request.source
        )
        return DocumentRecordDTO(
            field_reads=field_reads,
            structure_findings=dict(sample_read.structure_findings),
            overall_confidence=ReadConfidence.overall(field_reads=field_reads),
            low_confidence_fields=ReadConfidence.collect_low_confidence_field_keys(
                field_reads=field_reads
            ),
            boxes=self._build_boxes(sample_read),
            page_count=sample_read.page_count,
            deed_record=sample_read.deed_record,
            qr_fields=sample_read.qr_fields,
            quality=sample_read.quality,
        )

    def _read_sample(
        self, request: ExtractDocumentRequestDTO
    ) -> Optional[DocumentSampleRead]:
        segment = get_bundle_segment_read(
            filename=request.filename, page_start=request.page_start
        )
        if segment is not None:
            return segment.sample_read
        return get_sample_read(
            application_id=request.application_id,
            document_type_id=request.document_type_id,
            filename=request.filename,
        )

    def _classify_bundle(self, bundle: BundleSampleRead) -> DocumentClassificationDTO:
        document_type = self.catalog_service.get_document_type(
            document_type_id=bundle.document_type_id
        )
        return DocumentClassificationDTO(
            document_type_id=document_type.document_type_id,
            document_type_label=document_type.label,
            type_confidence=bundle.type_confidence,
            implemented=document_type.implemented,
            page_count=bundle.page_count,
            total_page_count=bundle.page_count,
            segments=tuple(
                self._build_segment(segment=segment) for segment in bundle.segments
            ),
        )

    def _classify_segment(
        self, segment: BundleSegmentRead
    ) -> DocumentClassificationDTO:
        """One document inside a bundle, already located and named by the pass that
        found it. Reading the slice again on its own would only lose that."""
        found = self._build_segment(segment=segment)
        return DocumentClassificationDTO(
            document_type_id=found.document_type_id,
            document_type_label=found.document_type_label,
            type_confidence=found.type_confidence,
            implemented=found.implemented,
            page_count=found.page_count,
            total_page_count=found.page_count,
            # Page numbers are relative to the slice, which is all this document is.
            segments=(
                DocumentSegmentDTO(
                    document_type_id=found.document_type_id,
                    document_type_label=found.document_type_label,
                    type_confidence=found.type_confidence,
                    implemented=found.implemented,
                    page_start=0,
                    page_end=found.page_count - 1,
                    summary=found.summary,
                    is_title_doc=found.is_title_doc,
                ),
            ),
        )

    def _build_segment(self, segment: BundleSegmentRead) -> DocumentSegmentDTO:
        document_type = self.catalog_service.get_document_type(
            document_type_id=segment.document_type_id
        )
        return DocumentSegmentDTO(
            document_type_id=document_type.document_type_id,
            document_type_label=document_type.label,
            type_confidence=segment.sample_read.type_confidence,
            implemented=document_type.implemented,
            page_start=segment.page_start,
            page_end=segment.page_end,
            summary=segment.summary,
            is_title_doc=segment.is_title_doc,
        )

    def _classify_by_sample(
        self, request: ExtractDocumentRequestDTO
    ) -> DocumentClassificationDTO:
        document_type = self._classify_by_filename(request.filename)
        sample_read = get_sample_read(
            application_id=request.application_id,
            document_type_id=document_type.document_type_id,
            filename=request.filename,
        )
        page_count = (
            sample_read.page_count if sample_read is not None else DEFAULT_PAGE_COUNT
        )
        return DocumentClassificationDTO(
            document_type_id=document_type.document_type_id,
            document_type_label=document_type.label,
            type_confidence=self._type_confidence(
                document_type=document_type, request=request, sample_read=sample_read
            ),
            implemented=document_type.implemented,
            page_count=page_count,
            total_page_count=page_count,
            segments=self._single_segment(
                document_type=document_type,
                page_count=page_count,
                type_confidence=self._type_confidence(
                    document_type=document_type,
                    request=request,
                    sample_read=sample_read,
                ),
            ),
        )

    @staticmethod
    def _single_segment(
        document_type: DocumentTypeDTO, page_count: int, type_confidence: float
    ) -> Tuple[DocumentSegmentDTO, ...]:
        return tuple(
            DocumentSegmentDTO(
                document_type_id=document_type.document_type_id,
                document_type_label=document_type.label,
                type_confidence=type_confidence,
                implemented=document_type.implemented,
                page_start=segment.page_start,
                page_end=segment.page_end,
                is_title_doc=segment.is_title_doc,
            )
            for segment in PageSegments.single(
                page_count=page_count,
                document_type_id=document_type.document_type_id,
            )
        )

    def _classify_by_filename(self, filename: str) -> DocumentTypeDTO:
        lowered_filename = str(filename or "").lower()
        for rule in self.catalog_service.get_filename_keyword_rules():
            if rule.keyword in lowered_filename:
                return self.catalog_service.get_document_type(
                    document_type_id=rule.document_type_id
                )
        return self.catalog_service.get_document_type(
            document_type_id=UNRECOGNISED_DOCUMENT_TYPE_ID
        )

    @staticmethod
    def _type_confidence(
        document_type: DocumentTypeDTO,
        request: ExtractDocumentRequestDTO,
        sample_read: Optional[DocumentSampleRead],
    ) -> float:
        if document_type.document_type_id == UNRECOGNISED_DOCUMENT_TYPE_ID:
            return UNRECOGNISED_TYPE_CONFIDENCE
        if request.source == DocumentSource.UPLOAD.value or sample_read is None:
            return KEYWORD_MATCH_TYPE_CONFIDENCE
        return sample_read.type_confidence

    @staticmethod
    def _build_field_reads(
        sample_read: DocumentSampleRead, source: str
    ) -> Tuple[FieldReadDTO, ...]:
        return tuple(
            FieldReadDTO(
                key=field_read.key,
                value=field_read.value,
                confidence=ReadConfidence.for_source(
                    confidence=field_read.confidence, source=source
                ),
            )
            for field_read in sample_read.field_reads
        )

    @staticmethod
    def _build_boxes(sample_read: DocumentSampleRead) -> Tuple[FieldBoxDTO, ...]:
        return tuple(
            FieldBoxDTO(
                field_key=field_read.key,
                value=field_read.value,
                page=0,
                box=field_read.box,
            )
            for field_read in sample_read.field_reads
        )
