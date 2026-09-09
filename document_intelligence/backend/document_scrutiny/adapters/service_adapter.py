class ServiceAdapter:
    @property
    def catalog_service(self):
        from document_catalog.app_interfaces.catalog_service_interface import (
            CatalogServiceInterface,
        )

        return CatalogServiceInterface()

    @property
    def extraction_service(self):
        from document_extraction.app_interfaces.extraction_service_interface import (
            ExtractionServiceInterface,
        )

        return ExtractionServiceInterface()

    @property
    def verification_service(self):
        from document_verification.app_interfaces.verification_service_interface import (
            VerificationServiceInterface,
        )

        return VerificationServiceInterface()


def get_service_adapter() -> ServiceAdapter:
    return ServiceAdapter()
