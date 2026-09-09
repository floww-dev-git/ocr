from typing import Mapping, Tuple

from document_catalog.dtos.catalog_dtos import IssuerServiceDTO
from document_scrutiny.constants.enums import CheckGroup, CheckStatus
from document_scrutiny.constants.issuer_check_constants import (
    DISAGREEING_FIELD_LABELS,
    ISSUER_CHECK_KEY,
    RETRY_ADVICE,
    IssuerAnswerOutcome,
    IssuerUnreachableReason,
)
from document_scrutiny.dtos.check_dtos import CheckDTO, IssuerCallDTO
from document_scrutiny.dtos.issuer_answer_dtos import IssuerAnswerFactsDTO

CONFIRMED_DETAIL = "The department's record matches the details read from this document."
NOT_MATCHED_DETAIL = (
    "The department's record does not match the details read from this document."
)
# The document type names itself, so an Aadhaar is never reported as a missing PAN.
NO_RECORD_DETAIL = (
    "The department has no record of this {document_type_label}. "
    "Check the number against the original."
)
PARTIAL_MATCH_DETAIL = (
    "The department holds this {document_type_label} but its record does not agree "
    "on {disagreeing}."
)
UNNAMED_DISAGREEMENT = "the details submitted"

_STATUSES_BY_OUTCOME: Mapping[str, str] = {
    IssuerAnswerOutcome.CONFIRMED.value: CheckStatus.PASS.value,
    IssuerAnswerOutcome.PARTIAL_MATCH.value: CheckStatus.WARN.value,
    IssuerAnswerOutcome.NOT_MATCHED.value: CheckStatus.FAIL.value,
    IssuerAnswerOutcome.NO_RECORD.value: CheckStatus.FAIL.value,
    IssuerAnswerOutcome.UNREACHABLE.value: CheckStatus.UNAVAILABLE.value,
}
_TITLE_SUFFIXES_BY_OUTCOME: Mapping[str, str] = {
    IssuerAnswerOutcome.CONFIRMED.value: "confirmed",
    IssuerAnswerOutcome.PARTIAL_MATCH.value: "did not fully match",
    IssuerAnswerOutcome.NOT_MATCHED.value: "did not match",
    IssuerAnswerOutcome.NO_RECORD.value: "has no record of this {document_type_label}",
    IssuerAnswerOutcome.UNREACHABLE.value: "did not respond",
}
_UNREACHABLE_EXPLANATIONS: Mapping[str, str] = {
    IssuerUnreachableReason.CONNECTION_FAILED.value: "The department could not be reached.",
    IssuerUnreachableReason.REFUSED_CREDENTIALS.value: (
        "The department refused this system's credentials."
    ),
    IssuerUnreachableReason.REJECTED_REQUEST.value: "The department rejected the request.",
    IssuerUnreachableReason.SERVER_ERROR.value: (
        "The department reported a problem at its end."
    ),
    IssuerUnreachableReason.UNREADABLE_ANSWER.value: (
        "The department answered in a form this system could not read."
    ),
}


class IssuerCheck:
    @classmethod
    def build(
        cls,
        document_id: str,
        issuer_service: IssuerServiceDTO,
        facts: IssuerAnswerFactsDTO,
        document_type_label: str,
    ) -> CheckDTO:
        outcome = cls._known_outcome(facts.outcome)
        return CheckDTO(
            check_id=f"{document_id}:{ISSUER_CHECK_KEY}",
            document_id=document_id,
            group=CheckGroup.EXTERNAL.value,
            title=cls._title(
                issuer_service=issuer_service,
                outcome=outcome,
                document_type_label=document_type_label,
            ),
            status=_STATUSES_BY_OUTCOME[outcome],
            detail=cls._detail(
                outcome=outcome,
                facts=facts,
                document_type_label=document_type_label,
            ),
            issuer_call=cls._build_issuer_call(
                issuer_service=issuer_service, facts=facts
            ),
        )

    @staticmethod
    def _title(
        issuer_service: IssuerServiceDTO, outcome: str, document_type_label: str
    ) -> str:
        suffix = _TITLE_SUFFIXES_BY_OUTCOME[outcome].format(
            document_type_label=document_type_label
        )
        return f"{issuer_service.name} {suffix}"

    @staticmethod
    def _known_outcome(outcome: str) -> str:
        if outcome in _STATUSES_BY_OUTCOME:
            return outcome
        return IssuerAnswerOutcome.UNREACHABLE.value

    @classmethod
    def _detail(
        cls, outcome: str, facts: IssuerAnswerFactsDTO, document_type_label: str
    ) -> str:
        if outcome == IssuerAnswerOutcome.CONFIRMED.value:
            return CONFIRMED_DETAIL
        if outcome == IssuerAnswerOutcome.NOT_MATCHED.value:
            return NOT_MATCHED_DETAIL
        if outcome == IssuerAnswerOutcome.NO_RECORD.value:
            return NO_RECORD_DETAIL.format(document_type_label=document_type_label)
        if outcome == IssuerAnswerOutcome.PARTIAL_MATCH.value:
            return cls._partial_match_detail(
                disagreeing_fields=facts.disagreeing_fields,
                document_type_label=document_type_label,
            )
        return cls._unreachable_detail(facts=facts)

    @staticmethod
    def _partial_match_detail(
        disagreeing_fields: Tuple[str, ...], document_type_label: str
    ) -> str:
        labels = [
            DISAGREEING_FIELD_LABELS[field_key]
            for field_key in disagreeing_fields
            if field_key in DISAGREEING_FIELD_LABELS
        ]
        joined = " and ".join(labels) if labels else UNNAMED_DISAGREEMENT
        return PARTIAL_MATCH_DETAIL.format(
            document_type_label=document_type_label, disagreeing=joined
        )

    @staticmethod
    def _unreachable_detail(facts: IssuerAnswerFactsDTO) -> str:
        # A timeout is the one reason where how long the officer waited is part of
        # what happened, so it is worded from the facts rather than a fixed string.
        # Every other reason is named explicitly, so a reason this system has not
        # been taught cannot silently render as a timeout.
        if facts.unreachable_reason == IssuerUnreachableReason.TIMED_OUT.value:
            return f"No response after {facts.latency_ms} ms. {RETRY_ADVICE}"
        explanation = _UNREACHABLE_EXPLANATIONS.get(
            str(facts.unreachable_reason),
            f"The department did not answer after {facts.latency_ms} ms.",
        )
        return f"{explanation} {RETRY_ADVICE}"

    @staticmethod
    def _build_issuer_call(
        issuer_service: IssuerServiceDTO, facts: IssuerAnswerFactsDTO
    ) -> IssuerCallDTO:
        return IssuerCallDTO(
            issuer_service_id=issuer_service.issuer_service_id,
            name=issuer_service.name,
            endpoint=issuer_service.endpoint,
            latency_ms=facts.latency_ms,
            request_payload=dict(facts.request_payload),
            response_payload=(
                dict(facts.response_payload)
                if facts.response_payload is not None
                else None
            ),
        )
