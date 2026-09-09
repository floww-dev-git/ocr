from document_scrutiny.constants.identifier_mask_constants import (
    MASKED_IDENTIFIER_LENGTH,
    MASK_TEMPLATE,
    VISIBLE_TAIL_LENGTH,
)


class IdentifierMask:
    """Hides all but the last four digits of an Aadhaar number.

    A check's detail is copied verbatim into the scrutiny note, which goes into the
    permanent municipal file, so a number the officer only needs to recognise must
    not be written out in full. Applied only at the documented length, so a PAN or
    a licence number is returned untouched rather than silently mangled.
    """

    @staticmethod
    def apply(value: str, masked: bool) -> str:
        digits = "".join(str(value or "").split())
        if not masked or len(digits) != MASKED_IDENTIFIER_LENGTH:
            return digits
        return MASK_TEMPLATE.format(tail=digits[-VISIBLE_TAIL_LENGTH:])
