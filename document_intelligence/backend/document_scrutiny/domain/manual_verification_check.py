from document_scrutiny.constants.enums import CheckGroup, CheckStatus
from document_scrutiny.constants.issuer_check_constants import ISSUER_CHECK_KEY
from document_scrutiny.dtos.check_dtos import CheckDTO

MANUAL_VERIFICATION_TITLE = "No department interface for this {document_type_label}"
MANUAL_VERIFICATION_DETAIL = (
    "The department that issues this document does not publish a verification "
    "interface, so nothing could be asked. Verify it against the original and mark "
    "it verified by hand."
)


class ManualVerificationCheck:
    """What stands in for a department's answer when there is no department to ask.

    Some issuing departments publish no verification interface at all. That is a
    fact about the document, not a failure of this run, so it is reported as a
    check of its own rather than left as a silent gap where an answer would be:
    the officer can see that nothing was asked, and why.

    It carries the same check id as a real issuer answer, so a document has one
    external check whether or not its department can be reached, and it carries no
    issuer call, because no call was made. It reports `info` rather than a status
    that would hold the thread open — an absent interface is not something the
    officer can resolve by chasing the applicant, and only the officer's own
    verification can close it.
    """

    @staticmethod
    def build(document_id: str, document_type_label: str) -> CheckDTO:
        return CheckDTO(
            check_id=f"{document_id}:{ISSUER_CHECK_KEY}",
            document_id=document_id,
            group=CheckGroup.EXTERNAL.value,
            title=MANUAL_VERIFICATION_TITLE.format(
                document_type_label=document_type_label
            ),
            status=CheckStatus.INFO.value,
            detail=MANUAL_VERIFICATION_DETAIL,
            issuer_call=None,
        )
