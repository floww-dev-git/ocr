from document_extraction.dtos.document_record_dtos import DocumentQualityDTO
from document_scrutiny.constants.enums import CheckGroup, CheckStatus
from document_scrutiny.domain.document_quality_check import (
    QUALITY_CHECK_KEY,
    DocumentQualityCheck,
)

DOCUMENT_ID = "document_1"


def quality(legible: bool, score: float, blur: float) -> DocumentQualityDTO:
    return DocumentQualityDTO(
        score=score, blur_score=blur, resolution_px=615, legible=legible
    )


class TestDocumentQualityCheck:
    def test_a_legible_scan_passes(self):
        check = DocumentQualityCheck.build(
            document_id=DOCUMENT_ID, quality=quality(legible=True, score=1.0, blur=800.0)
        )
        assert check is not None
        assert check.check_id == f"{DOCUMENT_ID}:{QUALITY_CHECK_KEY}"
        assert check.group == CheckGroup.RULE.value
        assert check.status == CheckStatus.PASS.value

    def test_a_poor_scan_warns_but_does_not_fail(self):
        # Arrange — a blurred photo of a real card is still a real card
        check = DocumentQualityCheck.build(
            document_id=DOCUMENT_ID, quality=quality(legible=False, score=0.07, blur=9.0)
        )

        # Assert
        assert check.status == CheckStatus.WARN.value
        assert "verify them against the original" in check.detail

    def test_no_assessment_reports_nothing_rather_than_a_false_pass(self):
        check = DocumentQualityCheck.build(document_id=DOCUMENT_ID, quality=None)
        assert check is None
