from typing import List, Mapping, Optional, Tuple

from document_scrutiny.constants.enums import CheckGroup, CheckStatus
from document_scrutiny.domain.name_similarity import NameSimilarity
from document_scrutiny.dtos.check_dtos import CheckDTO

QR_CONSISTENCY_CHECK_KEY = "qr-consistency"

# The fields worth comparing between what the QR carries and what is printed, with
# the label an officer reads for each.
_COMPARED_FIELDS: Tuple[Tuple[str, str], ...] = (
    ("name", "the name"),
    ("aadhaarNo", "the Aadhaar number"),
    ("dob", "the date of birth"),
)

# A printed name and a QR name this similar are treated as the same person; below
# it, a genuine disagreement. Reuses the engine's own name-match band.
_NAME_MATCH_FLOOR = 0.85

MATCH_TITLE = "QR code agrees with the printed details"
MATCH_DETAIL = (
    "The details encoded in the QR code match what is printed on the document."
)
CONTRADICTION_TITLE = "QR code contradicts the printed details"
NO_QR_TITLE = "No QR code was read"
NO_QR_DETAIL = (
    "No machine-readable QR code was found on this document, so the print could "
    "not be cross-checked against it."
)


class QrConsistencyCheck:
    """Whether a document's QR agrees with what is printed on its face.

    A genuine card's QR and its printed text carry the same identity. When they
    disagree, the print has been altered while the QR was left intact — a real,
    explainable integrity signal, and the honest form of tamper detection for these
    specimens (ADR-013). It compares only fields the QR actually carries against the
    same fields the model read off the print; anything the QR does not carry is not
    judged.
    """

    @classmethod
    def build(
        cls,
        document_id: str,
        qr_fields: Optional[Mapping[str, str]],
        printed_values: Mapping[str, str],
    ) -> CheckDTO:
        if not qr_fields:
            return cls._check(
                document_id=document_id,
                status=CheckStatus.INFO.value,
                title=NO_QR_TITLE,
                detail=NO_QR_DETAIL,
            )
        disagreements = cls._disagreements(
            qr_fields=qr_fields, printed_values=printed_values
        )
        if disagreements:
            return cls._check(
                document_id=document_id,
                status=CheckStatus.WARN.value,
                title=CONTRADICTION_TITLE,
                detail=cls._contradiction_detail(disagreements),
            )
        return cls._check(
            document_id=document_id,
            status=CheckStatus.PASS.value,
            title=MATCH_TITLE,
            detail=MATCH_DETAIL,
        )

    @classmethod
    def _disagreements(
        cls, qr_fields: Mapping[str, str], printed_values: Mapping[str, str]
    ) -> List[str]:
        disagreements = []
        for field_key, label in _COMPARED_FIELDS:
            qr_value = qr_fields.get(field_key)
            printed_value = printed_values.get(field_key)
            # Only compare a field the QR carries and the model actually read.
            if not qr_value or not printed_value:
                continue
            if not cls._agree(
                field_key=field_key, qr_value=qr_value, printed_value=printed_value
            ):
                disagreements.append(label)
        return disagreements

    @staticmethod
    def _agree(field_key: str, qr_value: str, printed_value: str) -> bool:
        if field_key == "name":
            return (
                NameSimilarity.calculate(
                    name=printed_value, comparison_name=qr_value
                )
                >= _NAME_MATCH_FLOOR
            )
        # Numbers and dates must match exactly once whitespace is ignored.
        return "".join(qr_value.split()).upper() == "".join(printed_value.split()).upper()

    @staticmethod
    def _contradiction_detail(disagreements: List[str]) -> str:
        joined = " and ".join(disagreements)
        return (
            f"The QR code and the printed document do not agree on {joined}. "
            "A genuine card carries the same details in both, so verify it against "
            "the original."
        )

    @staticmethod
    def _check(
        document_id: str, status: str, title: str, detail: str
    ) -> CheckDTO:
        return CheckDTO(
            check_id=f"{document_id}:{QR_CONSISTENCY_CHECK_KEY}",
            document_id=document_id,
            group=CheckGroup.RULE.value,
            title=title,
            status=status,
            detail=detail,
        )
