from typing import Mapping

from document_extraction.adapters.reads.aadhaar_card_read import AADHAAR_CARD_READ
from document_extraction.adapters.reads.conversion_certificate_read import (
    CONVERSION_CERTIFICATE_READ,
)
from document_extraction.adapters.reads.deed_read import (
    LINK_DOCUMENT_READ,
    SALE_DEED_READ,
)
from document_extraction.adapters.reads.driving_licence_read import (
    DRIVING_LICENCE_READ,
)
from document_extraction.adapters.reads.encumbrance_certificate_read import (
    ENCUMBRANCE_CERTIFICATE_READ,
)
from document_extraction.adapters.reads.irrigation_noc_read import IRRIGATION_NOC_READ
from document_extraction.adapters.reads.market_value_certificate_read import (
    MARKET_VALUE_CERTIFICATE_READ,
)
from document_extraction.adapters.reads.orc_read import ORC_READ
from document_extraction.adapters.reads.pan_card_read import PAN_CARD_READ
from document_extraction.adapters.reads.pattadar_passbook_read import (
    PATTADAR_PASSBOOK_READ,
)
from document_extraction.dtos.read_spec_dtos import DocumentReadSpec
from document_extraction.exceptions.extraction_exceptions import (
    DocumentReadNotRegistered,
)

# One entry per document type this build can actually read. A type declared in the
# catalog with `implemented=True` and no entry here is a wiring mistake, and it is
# reported as one rather than as an unreadable scan — see `get_document_read`.
READS_BY_DOCUMENT_TYPE: Mapping[str, DocumentReadSpec] = {
    AADHAAR_CARD_READ.document_type_id: AADHAAR_CARD_READ,
    CONVERSION_CERTIFICATE_READ.document_type_id: CONVERSION_CERTIFICATE_READ,
    DRIVING_LICENCE_READ.document_type_id: DRIVING_LICENCE_READ,
    ENCUMBRANCE_CERTIFICATE_READ.document_type_id: ENCUMBRANCE_CERTIFICATE_READ,
    IRRIGATION_NOC_READ.document_type_id: IRRIGATION_NOC_READ,
    MARKET_VALUE_CERTIFICATE_READ.document_type_id: MARKET_VALUE_CERTIFICATE_READ,
    ORC_READ.document_type_id: ORC_READ,
    PAN_CARD_READ.document_type_id: PAN_CARD_READ,
    PATTADAR_PASSBOOK_READ.document_type_id: PATTADAR_PASSBOOK_READ,
    LINK_DOCUMENT_READ.document_type_id: LINK_DOCUMENT_READ,
    SALE_DEED_READ.document_type_id: SALE_DEED_READ,
}


def get_document_read(document_type_id: str) -> DocumentReadSpec:
    """The schema, prompt and key maps for reading one document type.

    Raises rather than returning None. A missing entry means this build was asked
    to read a type it has no instructions for, and the one thing it must not do is
    fall through to another type's prompt and report the result as a genuine read.
    """
    read_spec = READS_BY_DOCUMENT_TYPE.get(str(document_type_id or ""))
    if read_spec is None:
        raise DocumentReadNotRegistered(document_type_id=str(document_type_id or ""))
    return read_spec


def is_bundleable(document_type_id: str) -> bool:
    """Whether a file of this type is worth an inventory pass.

    Answers False for a type this build cannot read, rather than raising: not
    knowing how to read something is a good enough reason not to go looking
    inside it for more of the same.
    """
    read_spec = READS_BY_DOCUMENT_TYPE.get(str(document_type_id or ""))
    return read_spec is not None and read_spec.bundleable
