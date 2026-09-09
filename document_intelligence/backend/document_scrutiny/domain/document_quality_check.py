from typing import Optional

from document_extraction.dtos.document_record_dtos import DocumentQualityDTO
from document_scrutiny.constants.enums import CheckGroup, CheckStatus
from document_scrutiny.dtos.check_dtos import CheckDTO

QUALITY_CHECK_KEY = "scan-quality"

LEGIBLE_TITLE = "Scan quality is good"
LEGIBLE_DETAIL = "The scan is clear enough to rely on what was read from it."
POOR_TITLE = "Scan quality is poor"
POOR_DETAIL = (
    "The scan is blurred or too low-resolution to read with confidence. Some "
    "details may have been misread; verify them against the original."
)


class DocumentQualityCheck:
    """Whether the scan is clear enough to trust what was read from it.

    A legibility judgement, not an authenticity one: it says nothing about whether
    the document is genuine, only whether the image is good enough that the reading
    can be relied on. A poor scan is a WARN, never a FAIL — a blurred photo of a
    real card is still a real card, and the remedy is a clearer copy, not rejection.
    Absent when quality was not assessed (e.g. the mock path), so nothing is
    reported rather than a false all-clear.
    """

    @classmethod
    def build(
        cls, document_id: str, quality: Optional[DocumentQualityDTO]
    ) -> Optional[CheckDTO]:
        if quality is None:
            return None
        legible = quality.legible
        return CheckDTO(
            check_id=f"{document_id}:{QUALITY_CHECK_KEY}",
            document_id=document_id,
            group=CheckGroup.RULE.value,
            title=LEGIBLE_TITLE if legible else POOR_TITLE,
            status=CheckStatus.PASS.value if legible else CheckStatus.WARN.value,
            detail=LEGIBLE_DETAIL if legible else POOR_DETAIL,
        )
