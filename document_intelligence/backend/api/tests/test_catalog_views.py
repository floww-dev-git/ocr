import pytest
from django.test import Client

EXPECTED_DOCUMENT_TYPE_COUNT = 16
EXPECTED_APPLICATION_COUNT = 6


class TestCatalogViews:
    @pytest.fixture
    def client(self):
        return Client()

    def test_posting_to_the_catalog_endpoint_is_rejected(self, client):
        # Act
        response = client.post("/api/catalog")

        # Assert
        assert response.status_code == 405

    def test_get_catalog_returns_every_document_type_marking_which_are_implemented(self, client):
        # Act
        response = client.get("/api/catalog")

        # Assert
        assert response.status_code == 200
        payload = response.json()
        assert len(payload["documentTypes"]) == EXPECTED_DOCUMENT_TYPE_COUNT
        implemented = [
            document_type["documentTypeId"]
            for document_type in payload["documentTypes"]
            if document_type["implemented"]
        ]
        assert implemented == [
            "aadhaar",
            "pan",
            "dl",
            "sale_deed",
            "link_doc",
            "ec",
            "irrigation_noc",
            "conversion_cert",
            "market_value_cert",
            "pattadar_passbook",
            "orc",
        ]

    def test_the_irrigation_noc_is_published_with_a_null_issuer_service(self, client):
        # Act
        payload = client.get("/api/catalog").json()

        # Assert — the frontend has to be able to tell "no department to ask" from
        # a department that exists, so the null travels rather than being omitted.
        irrigation_noc = next(
            document_type
            for document_type in payload["documentTypes"]
            if document_type["documentTypeId"] == "irrigation_noc"
        )
        assert irrigation_noc["implemented"] is True
        assert irrigation_noc["issuerServiceId"] is None
        assert irrigation_noc["previewLayout"] == "letter"

    def test_get_catalog_returns_the_order_services_and_application_field_specs(self, client):
        # Act
        payload = client.get("/api/catalog").json()

        # Assert
        assert len(payload["documentTypeOrder"]) == 15
        assert len(payload["issuerServices"]) == 7
        assert len(payload["applicationFieldSpecs"]) == 20

    def test_get_applications_returns_every_seeded_application(self, client):
        # Act
        response = client.get("/api/applications")

        # Assert
        assert response.status_code == 200
        applications = response.json()["applications"]
        assert len(applications) == EXPECTED_APPLICATION_COUNT
        assert applications[2]["applicationId"] == "BN/2026/0377"
        assert applications[2]["fieldValues"]["applicantName"] == "Mohammed Irfan Siddiqui"
