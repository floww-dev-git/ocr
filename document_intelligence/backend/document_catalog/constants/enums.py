import enum


class DocumentTypeEnum(enum.Enum):
    AADHAAR = "aadhaar"
    PAN = "pan"
    DRIVING_LICENCE = "dl"
    SALE_DEED = "sale_deed"
    LINK_DOCUMENT = "link_doc"
    ENCUMBRANCE_CERTIFICATE = "ec"
    TAX_RECEIPT = "tax_receipt"
    BUILDING_PERMIT = "building_permit"
    FIRE_NOC = "fire_noc"
    AAI_NOC = "aai_noc"
    IRRIGATION_NOC = "irrigation_noc"
    CONVERSION_CERT = "conversion_cert"
    MARKET_VALUE_CERT = "market_value_cert"
    PATTADAR_PASSBOOK = "pattadar_passbook"
    ORC = "orc"
    UNKNOWN = "unknown"


class IssuerServiceEnum(enum.Enum):
    UIDAI = "uidai"
    ITD_PAN = "itd_pan"
    SARATHI = "sarathi"
    IGRS = "igrs"
    FIRE_REGISTRY = "fire_registry"
    AAI_NOCAS = "aai_nocas"
    ULB_REGISTRY = "ulb_registry"


class FieldKind(enum.Enum):
    TEXT = "text"
    DATE = "date"
    IDENTIFIER = "id"
    NUMBER = "number"
    SELECT = "select"
    MONEY = "money"


class FieldComparisonRule(enum.Enum):
    ADDRESS_OVERLAP = "address_overlap"
    VALIDITY_WINDOW = "validity_window"
    EXTENT_TOLERANCE = "extent_tolerance"
    HEIGHT_AT_LEAST = "height_at_least"


class PreviewLayout(enum.Enum):
    CARD = "card"
    DEED = "deed"
    LETTER = "letter"
    GENERIC = "generic"


class DocumentIcon(enum.Enum):
    IDENTITY = "id"
    DEED = "deed"
    LETTER = "letter"
    FILE = "file"


class ApplicationFieldGroup(enum.Enum):
    APPLICANT = "Applicant"
    PLOT = "Plot"
    PROPOSAL = "Proposal"


class ApplicationFieldKey(enum.Enum):
    APPLICANT_NAME = "applicantName"
    PARENT_NAME = "parentName"
    DATE_OF_BIRTH = "dob"
    GENDER = "gender"
    AADHAAR_NUMBER = "aadhaarNo"
    PAN = "pan"
    MOBILE = "mobile"
    ADDRESS = "address"
    PLOT_NUMBER = "plotNo"
    SURVEY_NUMBER = "surveyNo"
    VILLAGE = "village"
    MANDAL = "mandal"
    DISTRICT = "district"
    URBAN_LOCAL_BODY = "ulb"
    EXTENT_SQ_YARD = "extentSqYd"
    PROPOSED_USE = "proposedUse"
    FLOORS = "floors"
    HEIGHT_METRES = "heightM"
    NEAR_WATER_BODY = "nearWaterBody"
    ROAD_WIDTH_METRES = "roadWidthM"
