from typing import Tuple

from document_extraction.dtos.extraction_dtos import DocumentSegmentDTO
from document_scrutiny.constants.enums import DocumentStage
from document_scrutiny.domain.bundle_check import BundleCheck
from document_scrutiny.domain.document_progress import DocumentProgress
from document_scrutiny.dtos.bundle_dtos import (
    BundleSegmentationDTO,
    SegmentBundleRequestDTO,
)
from document_scrutiny.dtos.document_dtos import DocumentStateDTO
from document_scrutiny.dtos.thread_dtos import (
    AddChildDocumentsDTO,
    ChildDocumentDTO,
    DocumentLookupDTO,
    UpdateDocumentDTO,
)
from document_scrutiny.storage_interfaces.scrutiny_thread_storage_interface import (
    ScrutinyThreadStorageInterface,
)


class SegmentBundleInteractor:
    """Turns one bundled file into the documents it actually holds.

    The bundle itself is closed off here rather than read: a file holding a current
    deed and the three deeds behind it has no single vendor, extent or registration
    number, so there is nothing to check against the application. What it has is
    contents, and those are listed as documents in their own right.
    """

    def __init__(self, thread_storage: ScrutinyThreadStorageInterface):
        self.thread_storage = thread_storage

    def segment_bundle(
        self, request: SegmentBundleRequestDTO
    ) -> BundleSegmentationDTO:
        document = self.thread_storage.get_document(
            lookup=DocumentLookupDTO(
                thread_id=request.thread_id, document_id=request.document_id
            )
        )
        children = self.thread_storage.add_child_documents(
            add_children=AddChildDocumentsDTO(
                thread_id=request.thread_id,
                parent_document_id=document.document_id,
                children=self._build_children(
                    document=document, segments=request.segments
                ),
            )
        )
        return BundleSegmentationDTO(
            parent=self._settle_parent(
                thread_id=request.thread_id,
                document=document,
                segments=request.segments,
            ),
            children=tuple(children),
        )

    @staticmethod
    def _build_children(
        document: DocumentStateDTO, segments: Tuple[DocumentSegmentDTO, ...]
    ) -> Tuple[ChildDocumentDTO, ...]:
        # Each child keeps the name of the file it came out of, because that is
        # where the officer will look for it; its page range tells them which part.
        return tuple(
            ChildDocumentDTO(
                filename=document.filename,
                file_format=document.file_format,
                file_size_bytes=document.file_size_bytes,
                document_type_id=segment.document_type_id,
                document_type_label=segment.document_type_label,
                type_confidence=segment.type_confidence,
                implemented=segment.implemented,
                page_start=segment.page_start,
                page_end=segment.page_end,
            )
            for segment in segments
        )

    def _settle_parent(
        self,
        thread_id: str,
        document: DocumentStateDTO,
        segments: Tuple[DocumentSegmentDTO, ...],
    ) -> DocumentStateDTO:
        settled = DocumentProgress.with_stage(
            document=document,
            stage=DocumentStage.DONE.value,
            checks=document.checks
            + (
                BundleCheck.build(
                    document_id=document.document_id, segments=segments
                ),
            ),
        )
        return self.thread_storage.update_document(
            update_document=UpdateDocumentDTO(thread_id=thread_id, document=settled)
        )
