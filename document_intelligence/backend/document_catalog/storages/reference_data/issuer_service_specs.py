from typing import Tuple

from document_catalog.constants.enums import IssuerServiceEnum
from document_catalog.dtos.catalog_dtos import IssuerServiceDTO

ISSUER_SERVICE_SPECS: Tuple[IssuerServiceDTO, ...] = (
    IssuerServiceDTO(
        issuer_service_id=IssuerServiceEnum.UIDAI.value,
        name="UIDAI Aadhaar verification",
        latency_ms=1400,
        endpoint="POST /authserver/2.5/demoauth",
    ),
    IssuerServiceDTO(
        issuer_service_id=IssuerServiceEnum.ITD_PAN.value,
        name="Income Tax PAN verification",
        latency_ms=900,
        endpoint="POST /pan/verify",
    ),
    IssuerServiceDTO(
        issuer_service_id=IssuerServiceEnum.SARATHI.value,
        name="Sarathi driving licence check",
        latency_ms=1200,
        endpoint="GET /dl/{dlNo}",
    ),
    IssuerServiceDTO(
        issuer_service_id=IssuerServiceEnum.IGRS.value,
        name="IGRS registered deed lookup",
        latency_ms=1800,
        endpoint="GET /igrs/deeds/{docNo}",
    ),
    IssuerServiceDTO(
        issuer_service_id=IssuerServiceEnum.FIRE_REGISTRY.value,
        name="Fire Services NOC registry",
        latency_ms=1100,
        endpoint="GET /fire/noc/{nocNo}",
    ),
    IssuerServiceDTO(
        issuer_service_id=IssuerServiceEnum.AAI_NOCAS.value,
        name="AAI NOCAS height clearance",
        latency_ms=1500,
        endpoint="GET /nocas/noc/{nocId}",
    ),
    IssuerServiceDTO(
        issuer_service_id=IssuerServiceEnum.ULB_REGISTRY.value,
        name="ULB building permit registry",
        latency_ms=700,
        endpoint="GET /permits/{permitNo}",
    ),
)
