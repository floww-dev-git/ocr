import enum


class IdentifierField(enum.Enum):
    """Document field keys carrying an identifier with a published structure.

    Field keys, not application field keys: a driving licence number has nothing on
    the application form to compare against and its shape is still checkable.
    """

    PAN = "pan"
    AADHAAR_NUMBER = "aadhaarNo"
    LICENCE_NUMBER = "dlNo"
