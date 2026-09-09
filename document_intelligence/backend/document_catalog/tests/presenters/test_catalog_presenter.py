import pytest

from document_catalog.constants.enums import (
    ApplicationFieldKey,
    FieldComparisonRule,
    FieldKind,
)
from document_catalog.dtos.catalog_dtos import DocumentCatalogDTO
from document_catalog.tests.factories.catalog_dto_factories import (
    ApplicationDTOFactory,
    ApplicationFieldSpecDTOFactory,
    DocumentTypeDTOFactory,
    FieldSpecDTOFactory,
    IssuerServiceDTOFactory,
    StructureSpecDTOFactory,
)


class TestCatalogPresenter:
    @pytest.fixture
    def presenter(self):
        from document_catalog.presenters.catalog_presenter import CatalogPresenter

        return CatalogPresenter()

    def test_an_empty_catalog_presents_empty_lists_rather_than_null(self, presenter):
        # Arrange
        catalog = DocumentCatalogDTO(
            document_types=(),
            document_type_order=(),
            issuer_services=(),
            application_field_specs=(),
        )

        # Act
        presented = presenter.get_document_catalog_response(catalog=catalog)

        # Assert
        assert presented == {
            "documentTypes": [],
            "documentTypeOrder": [],
            "issuerServices": [],
            "applicationFieldSpecs": [],
        }

    def test_presents_every_document_type_field_the_frontend_contract_needs(self, presenter):
        # Arrange
        field_spec = FieldSpecDTOFactory(
            key="name",
            label="Name",
            kind=FieldKind.TEXT.value,
            application_field_key=ApplicationFieldKey.APPLICANT_NAME.value,
            masked=True,
            comparison_rule=FieldComparisonRule.ADDRESS_OVERLAP.value,
        )
        document_type = DocumentTypeDTOFactory(
            document_type_id="pan",
            label="PAN",
            issuer_service_id="itd_pan",
            implemented=True,
            field_specs=(field_spec,),
            structure_specs=(StructureSpecDTOFactory(key="photo", label="Photograph"),),
        )
        catalog = DocumentCatalogDTO(
            document_types=(document_type,),
            document_type_order=("pan",),
            issuer_services=(),
            application_field_specs=(),
        )

        # Act
        presented = presenter.get_document_catalog_response(catalog=catalog)

        # Assert
        assert presented["documentTypes"] == [
            {
                "documentTypeId": "pan",
                "label": "PAN",
                "icon": document_type.icon,
                "previewLayout": document_type.preview_layout,
                "issuerServiceId": "itd_pan",
                "implemented": True,
                "fieldSpecs": [
                    {
                        "key": "name",
                        "label": "Name",
                        "kind": FieldKind.TEXT.value,
                        "applicationFieldKey": ApplicationFieldKey.APPLICANT_NAME.value,
                        "masked": True,
                        "comparisonRule": FieldComparisonRule.ADDRESS_OVERLAP.value,
                    }
                ],
                "structureSpecs": [{"key": "photo", "label": "Photograph"}],
            }
        ]

    def test_presents_issuer_services_and_application_field_specs(self, presenter):
        # Arrange
        catalog = DocumentCatalogDTO(
            document_types=(),
            document_type_order=(),
            issuer_services=(
                IssuerServiceDTOFactory(
                    issuer_service_id="itd_pan",
                    name="Income Tax PAN verification",
                    latency_ms=900,
                    endpoint="POST /pan/verify",
                ),
            ),
            application_field_specs=(
                ApplicationFieldSpecDTOFactory(
                    key="gender",
                    label="Gender",
                    kind=FieldKind.SELECT.value,
                    group="Applicant",
                    options=("Male", "Female", "Other"),
                ),
            ),
        )

        # Act
        presented = presenter.get_document_catalog_response(catalog=catalog)

        # Assert
        assert presented["issuerServices"] == [
            {
                "issuerServiceId": "itd_pan",
                "name": "Income Tax PAN verification",
                "latencyMs": 900,
                "endpoint": "POST /pan/verify",
            }
        ]
        assert presented["applicationFieldSpecs"] == [
            {
                "key": "gender",
                "label": "Gender",
                "kind": FieldKind.SELECT.value,
                "group": "Applicant",
                "masked": False,
                "options": ["Male", "Female", "Other"],
            }
        ]

    def test_presents_applications_with_their_field_values(self, presenter):
        # Arrange
        applications = [
            ApplicationDTOFactory(
                application_id="BN/2026/0421",
                status="Under scrutiny",
                field_values={"applicantName": "Srinivas Rao Kandula", "pan": "DQRPK4831L"},
            )
        ]

        # Act
        presented = presenter.get_applications_response(applications=applications)

        # Assert
        assert presented == {
            "applications": [
                {
                    "applicationId": "BN/2026/0421",
                    "status": "Under scrutiny",
                    "fieldValues": {
                        "applicantName": "Srinivas Rao Kandula",
                        "pan": "DQRPK4831L",
                    },
                }
            ]
        }
