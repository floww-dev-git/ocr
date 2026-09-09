import pytest


class StorageMock:
    @pytest.fixture
    def catalog_storage(self):
        from unittest.mock import create_autospec

        from document_catalog.storage_interfaces.catalog_storage_interface import (
            CatalogStorageInterface,
        )

        return create_autospec(CatalogStorageInterface)

    @pytest.fixture
    def application_storage(self):
        from unittest.mock import create_autospec

        from document_catalog.storage_interfaces.application_storage_interface import (
            ApplicationStorageInterface,
        )

        return create_autospec(ApplicationStorageInterface)
