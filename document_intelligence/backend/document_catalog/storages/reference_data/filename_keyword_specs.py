from typing import Tuple

from document_catalog.constants.enums import DocumentTypeEnum
from document_catalog.dtos.catalog_dtos import FilenameKeywordRuleDTO

# First match wins, so the order matters. The land-record keywords sit ahead of the
# identity keywords for one specific reason: "occupancy" contains "pan"
# ("occu-pan-cy"), so an ORC filename would otherwise route to PAN. Keeping the
# revenue/land group first keeps each of these documents matching its own keyword.
_KEYWORD_TO_DOCUMENT_TYPE = (
    ("encumbrance", DocumentTypeEnum.ENCUMBRANCE_CERTIFICATE),
    ("_ec", DocumentTypeEnum.ENCUMBRANCE_CERTIFICATE),
    ("ec_", DocumentTypeEnum.ENCUMBRANCE_CERTIFICATE),
    # Land conversion (NALA) certificate.
    ("conversion", DocumentTypeEnum.CONVERSION_CERT),
    ("nala", DocumentTypeEnum.CONVERSION_CERT),
    # Market value certificate. "mvc" covers the abbreviated form; "market" alone is
    # enough for the usual filename.
    ("market", DocumentTypeEnum.MARKET_VALUE_CERT),
    ("mvc", DocumentTypeEnum.MARKET_VALUE_CERT),
    # Pattadar pass book / title deed (Dharani). "pattadar" is checked before the
    # shorter "patta" so a full name is not misattributed, though both route here.
    ("pattadar", DocumentTypeEnum.PATTADAR_PASSBOOK),
    ("passbook", DocumentTypeEnum.PATTADAR_PASSBOOK),
    ("dharani", DocumentTypeEnum.PATTADAR_PASSBOOK),
    ("patta", DocumentTypeEnum.PATTADAR_PASSBOOK),
    # Occupancy rights certificate for Inam lands. Ahead of "pan" on purpose (see
    # the note above): "occupancy" would otherwise be caught by the "pan" rule.
    ("orc", DocumentTypeEnum.ORC),
    ("inam", DocumentTypeEnum.ORC),
    ("occupancy", DocumentTypeEnum.ORC),
    ("aadhaar", DocumentTypeEnum.AADHAAR),
    ("aadhar", DocumentTypeEnum.AADHAAR),
    ("uid", DocumentTypeEnum.AADHAAR),
    ("pan", DocumentTypeEnum.PAN),
    ("licence", DocumentTypeEnum.DRIVING_LICENCE),
    ("license", DocumentTypeEnum.DRIVING_LICENCE),
    ("_dl", DocumentTypeEnum.DRIVING_LICENCE),
    ("dl_", DocumentTypeEnum.DRIVING_LICENCE),
    ("driving", DocumentTypeEnum.DRIVING_LICENCE),
    ("link", DocumentTypeEnum.LINK_DOCUMENT),
    ("sale", DocumentTypeEnum.SALE_DEED),
    ("deed", DocumentTypeEnum.SALE_DEED),
    ("permit", DocumentTypeEnum.BUILDING_PERMIT),
    ("permission", DocumentTypeEnum.BUILDING_PERMIT),
    ("sanction", DocumentTypeEnum.BUILDING_PERMIT),
    ("fire", DocumentTypeEnum.FIRE_NOC),
    ("aai", DocumentTypeEnum.AAI_NOC),
    ("airport", DocumentTypeEnum.AAI_NOC),
    ("nocas", DocumentTypeEnum.AAI_NOC),
    ("irrigation", DocumentTypeEnum.IRRIGATION_NOC),
    ("ftl", DocumentTypeEnum.IRRIGATION_NOC),
    ("tax", DocumentTypeEnum.TAX_RECEIPT),
    ("receipt", DocumentTypeEnum.TAX_RECEIPT),
)

FILENAME_KEYWORD_RULES: Tuple[FilenameKeywordRuleDTO, ...] = tuple(
    FilenameKeywordRuleDTO(keyword=keyword, document_type_id=document_type.value)
    for keyword, document_type in _KEYWORD_TO_DOCUMENT_TYPE
)
