# An Aadhaar number is twelve digits, and UIDAI's own convention shows only the
# last four. Any other length is left alone: a PAN or a licence number carries no
# such convention, and a partial mask would just be an unreadable value.
MASKED_IDENTIFIER_LENGTH = 12
VISIBLE_TAIL_LENGTH = 4
MASK_TEMPLATE = "XXXX XXXX {tail}"
