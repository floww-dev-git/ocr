import dataclasses
from typing import List, Sequence, Tuple

from django.conf import settings

from document_catalog.dtos.catalog_dtos import DocumentTypeDTO
from document_extraction.adapters.document_extractor_interface import (
    DocumentExtractorInterface,
)
from document_extraction.adapters.gemini_client import (
    build_image_parts,
    build_text_part,
    generate_parsed,
)
from document_extraction.adapters.gemini_prompts import CLASSIFY_PROMPT
from document_extraction.adapters.gemini_schemas import DocumentIdentification
from document_extraction.adapters.image_quality import assess_quality
from document_extraction.adapters.page_images import downscale_png, render_page_images
from document_extraction.adapters.qr_decode import decode_qr_fields
from document_extraction.adapters.reads.document_read_registry import (
    get_document_read,
    is_bundleable,
)
from document_extraction.adapters.reads.field_read_mapper import FieldReadMapper
from document_extraction.adapters.reads.file_inventory_read import (
    INVENTORY_PROMPT,
    PageMap,
    read_page_boundaries,
)
from document_extraction.adapters.service_adapter import get_service_adapter
from document_extraction.constants.extraction_constants import (
    INVENTORY_TYPE_CONFIDENCE,
)
from document_extraction.domain.page_segments import PageSegments
from document_extraction.dtos.document_record_dtos import DocumentRecordDTO
from document_extraction.dtos.extraction_dtos import (
    DocumentClassificationDTO,
    DocumentSegmentDTO,
    ExtractDocumentRequestDTO,
)
from document_extraction.dtos.inventory_dtos import PageSegmentDTO
from document_extraction.dtos.read_spec_dtos import DocumentReadSpec
from document_extraction.exceptions.extraction_exceptions import ExtractionFailed

UNRECOGNISED_DOCUMENT_TYPE_ID = "unknown"
NO_MODEL_RESPONSE = "The model returned no readable response."
SINGLE_PAGE_COUNT = 1


class GeminiDocumentExtractor(DocumentExtractorInterface):
    @property
    def catalog_service(self):
        return get_service_adapter().catalog_service

    def classify_document(
        self, request: ExtractDocumentRequestDTO
    ) -> DocumentClassificationDTO:
        page_images, total_page_count = self._render(request)
        identification = self._identify(request=request, page_images=page_images)
        document_type = self._resolve_document_type(identification.document_type_id)
        return DocumentClassificationDTO(
            document_type_id=document_type.document_type_id,
            document_type_label=document_type.label,
            type_confidence=round(float(identification.confidence or 0.0), 2),
            implemented=document_type.implemented,
            page_count=len(page_images),
            total_page_count=total_page_count,
            segments=self._read_segments(
                request=request,
                page_images=page_images,
                document_type=document_type,
            ),
        )

    def extract_document_record(
        self, request: ExtractDocumentRequestDTO
    ) -> DocumentRecordDTO:
        # The type decided at classify time chooses the schema and the prompt, so a
        # card is never read with a deed's instructions.
        read_spec = self._read_spec(request)
        page_images, _ = self._render(request)
        parts = build_image_parts(page_images)
        parts.append(build_text_part(text=read_spec.prompt))
        model_read = self._call_model(
            request=request,
            parts=parts,
            model=settings.EXTRACTION_MODEL,
            response_schema=read_spec.response_schema,
        )
        mapper = read_spec.record_mapper or FieldReadMapper
        record = mapper.to_document_record(
            model_read=model_read,
            read_spec=read_spec,
            source=request.source,
            page_count=len(page_images),
        )
        # What the page itself carries beyond the model's reading: a QR to compare
        # against the print, and how legible the scan is. Added here, on the real
        # image, because the mapper only sees the model's answer.
        return dataclasses.replace(
            record,
            qr_fields=decode_qr_fields(page_images),
            quality=assess_quality(page_images),
        )

    @staticmethod
    def _read_spec(request: ExtractDocumentRequestDTO) -> DocumentReadSpec:
        return get_document_read(document_type_id=request.document_type_id)

    def _read_segments(
        self,
        request: ExtractDocumentRequestDTO,
        page_images: List[bytes],
        document_type: DocumentTypeDTO,
    ) -> Tuple[DocumentSegmentDTO, ...]:
        page_count = len(page_images)
        if not self._worth_an_inventory(
            request=request, page_count=page_count, document_type=document_type
        ):
            return self._decorate(
                PageSegments.single(
                    page_count=page_count,
                    document_type_id=document_type.document_type_id,
                )
            )
        found = PageSegments.group(
            boundaries=self._inventory(request=request, page_images=page_images),
            page_count=page_count,
        )
        return self._decorate(found)

    @staticmethod
    def _worth_an_inventory(
        request: ExtractDocumentRequestDTO,
        page_count: int,
        document_type: DocumentTypeDTO,
    ) -> bool:
        # A slice was already carved out of a bundle, and one page cannot hold two
        # registered documents, so neither is worth a second model call.
        return (
            not request.is_page_slice
            and page_count > SINGLE_PAGE_COUNT
            and is_bundleable(document_type_id=document_type.document_type_id)
        )

    def _inventory(
        self, request: ExtractDocumentRequestDTO, page_images: List[bytes]
    ):
        """Pass one, from the POC: every page is sent, so no link deed is missed."""
        parts = build_image_parts([downscale_png(page) for page in page_images])
        parts.append(build_text_part(text=INVENTORY_PROMPT))
        page_map = self._call_model(
            request=request,
            parts=parts,
            model=settings.INVENTORY_MODEL,
            response_schema=PageMap,
        )
        return read_page_boundaries(page_map=page_map)

    def _decorate(
        self, segments: Sequence[PageSegmentDTO]
    ) -> Tuple[DocumentSegmentDTO, ...]:
        """Names each found document in the catalog's own terms."""
        return tuple(
            self._decorate_one(segment=segment) for segment in segments
        )

    def _decorate_one(self, segment: PageSegmentDTO) -> DocumentSegmentDTO:
        document_type = self._resolve_document_type(segment.document_type_id)
        return DocumentSegmentDTO(
            document_type_id=document_type.document_type_id,
            document_type_label=document_type.label,
            type_confidence=INVENTORY_TYPE_CONFIDENCE,
            implemented=document_type.implemented,
            page_start=segment.page_start,
            page_end=segment.page_end,
            summary=segment.summary,
            is_title_doc=segment.is_title_doc,
        )

    def _identify(
        self, request: ExtractDocumentRequestDTO, page_images: List[bytes]
    ) -> DocumentIdentification:
        parts = build_image_parts([downscale_png(page) for page in page_images])
        parts.append(build_text_part(text=self._classify_prompt()))
        return self._call_model(
            request=request,
            parts=parts,
            model=settings.INVENTORY_MODEL,
            response_schema=DocumentIdentification,
        )

    def _classify_prompt(self) -> str:
        options = "\n".join(
            f"- {document_type.document_type_id}: {document_type.label}"
            for document_type in self.catalog_service.get_document_types()
        )
        return CLASSIFY_PROMPT.format(document_type_options=options)

    def _call_model(
        self,
        request: ExtractDocumentRequestDTO,
        parts: list,
        model: str,
        response_schema,
    ):
        try:
            parsed = generate_parsed(
                model=model, parts=parts, response_schema=response_schema
            )
        except Exception as error:
            raise ExtractionFailed(
                filename=request.filename, reason=str(error)
            ) from error
        if parsed is None:
            raise ExtractionFailed(filename=request.filename, reason=NO_MODEL_RESPONSE)
        return parsed

    def _resolve_document_type(self, document_type_id: str) -> DocumentTypeDTO:
        from document_catalog.exceptions.catalog_exceptions import DocumentTypeNotFound

        try:
            return self.catalog_service.get_document_type(
                document_type_id=str(document_type_id or "")
            )
        except DocumentTypeNotFound:
            return self.catalog_service.get_document_type(
                document_type_id=UNRECOGNISED_DOCUMENT_TYPE_ID
            )

    @classmethod
    def _render(cls, request: ExtractDocumentRequestDTO) -> Tuple[List[bytes], int]:
        if not request.file_path:
            raise ExtractionFailed(
                filename=request.filename,
                reason="Real extraction needs the stored file; none was recorded.",
            )
        pages, total_page_count = render_page_images(file_path=request.file_path)
        return cls._slice(request=request, pages=pages), total_page_count

    @staticmethod
    def _slice(
        request: ExtractDocumentRequestDTO, pages: List[bytes]
    ) -> List[bytes]:
        """The pages of one document inside a bundled file.

        A slice that falls outside the file leaves nothing to read, and reporting
        that is better than silently reading the wrong deed.
        """
        if not request.is_page_slice:
            return pages
        page_start = max(0, int(request.page_start or 0))
        page_end = int(request.page_end if request.page_end is not None else page_start)
        sliced = pages[page_start : page_end + 1]
        if not sliced:
            raise ExtractionFailed(
                filename=request.filename,
                reason=(
                    f"Pages {page_start + 1}-{page_end + 1} are not in this file, "
                    f"which has {len(pages)}."
                ),
            )
        return sliced
