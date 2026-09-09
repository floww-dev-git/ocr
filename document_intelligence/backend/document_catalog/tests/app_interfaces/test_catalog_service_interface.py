import pytest

from document_catalog.constants.enums import DocumentTypeEnum, IssuerServiceEnum
from document_catalog.exceptions.catalog_exceptions import (
    ApplicationNotFound,
    DocumentTypeNotFound,
    IssuerServiceNotFound,
)


class TestCatalogServiceInterface:
    @pytest.fixture
    def service_interface(self):
        from document_catalog.app_interfaces.catalog_service_interface import (
            CatalogServiceInterface,
        )

        return CatalogServiceInterface()

    def test_an_unknown_document_type_propagates_the_domain_exception(self, service_interface):
        # Act & Assert
        with pytest.raises(DocumentTypeNotFound):
            service_interface.get_document_type(document_type_id="ration_card")

    def test_an_unknown_issuer_service_propagates_the_domain_exception(self, service_interface):
        # Act & Assert
        with pytest.raises(IssuerServiceNotFound):
            service_interface.get_issuer_service(issuer_service_id="passport_seva")

    def test_an_unknown_application_propagates_the_domain_exception(self, service_interface):
        # Act & Assert
        with pytest.raises(ApplicationNotFound):
            service_interface.get_application(application_id="BN/2026/9999")

    def test_exposes_the_pan_document_type_to_consuming_apps(self, service_interface):
        # Act
        pan_type = service_interface.get_document_type(
            document_type_id=DocumentTypeEnum.PAN.value
        )

        # Assert
        assert pan_type.implemented is True
        assert pan_type.issuer_service_id == IssuerServiceEnum.ITD_PAN.value

    def test_exposes_the_document_types_filename_rules_and_applications(self, service_interface):
        # Act
        document_types = service_interface.get_document_types()
        keyword_rules = service_interface.get_filename_keyword_rules()
        application = service_interface.get_application(application_id="BN/2026/0377")

        # Assert
        assert len(document_types) == 16
        assert any(rule.keyword == "pan" for rule in keyword_rules)
        assert application.field_values["pan"] == "BNMPS7720K"
