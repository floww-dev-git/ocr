class ServiceAdapter:
    @property
    def catalog_service(self):
        from document_catalog.app_interfaces.catalog_service_interface import (
            CatalogServiceInterface,
        )

        return CatalogServiceInterface()


def get_service_adapter() -> ServiceAdapter:
    return ServiceAdapter()
