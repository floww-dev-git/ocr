import enum

from document_catalog.constants.enums import DocumentTypeEnum

LOW_CONFIDENCE_THRESHOLD = 0.8
UPLOAD_CONFIDENCE_FACTOR = 0.85
CONFIDENCE_DECIMAL_PLACES = 2
KEYWORD_MATCH_TYPE_CONFIDENCE = 0.87
UNRECOGNISED_TYPE_CONFIDENCE = 0.41
UNCERTAIN_FIELD_CONFIDENCE = 0.55
BOX_COORDINATE_SCALE = 1000
BOX_COORDINATE_COUNT = 4
GEMINI_API_KEY_VARIABLE = "GEMINI_API_KEY"


class ExtractionMode(enum.Enum):
    MOCK = "mock"
    GEMINI = "gemini"


class DocumentSource(enum.Enum):
    UPLOAD = "upload"
    SAMPLE = "sample"


# Carried from sale_deed_poc/build/poc/extract.py::_TITLE_KINDS. A deed of one of
# these kinds conveys title; an "agreement to sell" of the same kind does not,
# which is why the word disqualifies a match.
TITLE_DEED_KINDS = (
    "sale",
    "gift",
    "partition",
    "settlement",
    "release",
    "conveyance",
)
NON_TITLE_WORD = "agreement"

# The inventory pass names what it found in the registrar's own words, not in
# catalog ids. First keyword wins, so the order is the priority.
INVENTORY_TYPE_KEYWORDS = (
    ("encumbrance", DocumentTypeEnum.ENCUMBRANCE_CERTIFICATE.value),
    ("tax", DocumentTypeEnum.TAX_RECEIPT.value),
    ("receipt", DocumentTypeEnum.TAX_RECEIPT.value),
    ("permit", DocumentTypeEnum.BUILDING_PERMIT.value),
    ("sanction", DocumentTypeEnum.BUILDING_PERMIT.value),
    ("sale", DocumentTypeEnum.SALE_DEED.value),
)
INVENTORY_FALLBACK_TYPE_ID = DocumentTypeEnum.UNKNOWN.value
# A title deed that is not a sale — a gift, a partition, a settlement — is still a
# link in the chain, and "link document" is the catalog's name for exactly that.
# The same id names a prior sale deed in a bundle, for the same reason.
PRIOR_TITLE_TYPE_ID = DocumentTypeEnum.LINK_DOCUMENT.value
TITLE_DEED_TYPE_IDS = (
    DocumentTypeEnum.SALE_DEED.value,
    DocumentTypeEnum.LINK_DOCUMENT.value,
)
INVENTORY_TYPE_CONFIDENCE = 0.82
