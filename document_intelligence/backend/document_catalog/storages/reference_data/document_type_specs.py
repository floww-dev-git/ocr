from typing import Tuple

from document_catalog.constants.enums import DocumentTypeEnum
from document_catalog.dtos.catalog_dtos import DocumentTypeDTO
from document_catalog.storages.reference_data.clearance_document_specs import (
    CLEARANCE_DOCUMENT_SPECS,
)
from document_catalog.storages.reference_data.identity_document_specs import (
    IDENTITY_DOCUMENT_SPECS,
)
from document_catalog.storages.reference_data.land_document_specs import (
    LAND_DOCUMENT_SPECS,
)
from document_catalog.storages.reference_data.property_document_specs import (
    PROPERTY_DOCUMENT_SPECS,
)

DOCUMENT_TYPE_SPECS: Tuple[DocumentTypeDTO, ...] = (
    IDENTITY_DOCUMENT_SPECS
    + PROPERTY_DOCUMENT_SPECS
    + CLEARANCE_DOCUMENT_SPECS
    + LAND_DOCUMENT_SPECS
)

DOCUMENT_TYPE_ORDER: Tuple[str, ...] = (
    DocumentTypeEnum.AADHAAR.value,
    DocumentTypeEnum.PAN.value,
    DocumentTypeEnum.DRIVING_LICENCE.value,
    DocumentTypeEnum.SALE_DEED.value,
    DocumentTypeEnum.LINK_DOCUMENT.value,
    DocumentTypeEnum.ENCUMBRANCE_CERTIFICATE.value,
    DocumentTypeEnum.CONVERSION_CERT.value,
    DocumentTypeEnum.MARKET_VALUE_CERT.value,
    DocumentTypeEnum.PATTADAR_PASSBOOK.value,
    DocumentTypeEnum.ORC.value,
    DocumentTypeEnum.TAX_RECEIPT.value,
    DocumentTypeEnum.BUILDING_PERMIT.value,
    DocumentTypeEnum.FIRE_NOC.value,
    DocumentTypeEnum.AAI_NOC.value,
    DocumentTypeEnum.IRRIGATION_NOC.value,
)
