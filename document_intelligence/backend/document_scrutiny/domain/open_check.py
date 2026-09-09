from document_scrutiny.constants.enums import CheckStatus
from document_scrutiny.dtos.check_dtos import CheckDTO

RESOLVABLE_STATUSES = (
    CheckStatus.FAIL.value,
    CheckStatus.WARN.value,
    CheckStatus.UNAVAILABLE.value,
)


def is_open(check: CheckDTO) -> bool:
    disagrees = check.status in RESOLVABLE_STATUSES
    return disagrees and not check.acknowledged and not check.manual
