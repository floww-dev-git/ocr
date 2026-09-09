import pytest

from document_catalog.constants.enums import DocumentTypeEnum, IssuerServiceEnum
from document_catalog.exceptions.catalog_exceptions import (
    DocumentTypeNotFound,
    IssuerServiceNotFound,
)

EXPECTED_DOCUMENT_TYPE_COUNT = 16
EXPECTED_ORDERED_TYPE_COUNT = 15


class TestInMemoryCatalogStorage:
    @pytest.fixture
    def storage(self):
        from document_catalog.storages.in_memory_catalog_storage import (
            InMemoryCatalogStorage,
        )

        return InMemoryCatalogStorage()

    def test_get_document_type_with_unknown_id_raises_document_type_not_found(self, storage):
        # Arrange
        unknown_document_type_id = "ration_card"

        # Act & Assert
        with pytest.raises(DocumentTypeNotFound) as exception_info:
            storage.get_document_type(document_type_id=unknown_document_type_id)
        assert exception_info.value.document_type_id == unknown_document_type_id

    def test_get_issuer_service_with_unknown_id_raises_issuer_service_not_found(self, storage):
        # Arrange
        unknown_issuer_service_id = "passport_seva"

        # Act & Assert
        with pytest.raises(IssuerServiceNotFound) as exception_info:
            storage.get_issuer_service(issuer_service_id=unknown_issuer_service_id)
        assert exception_info.value.issuer_service_id == unknown_issuer_service_id

    def test_get_document_types_returns_every_prototype_type_marking_the_implemented(
        self, storage
    ):
        # Act
        document_types = storage.get_document_types()

        # Assert
        assert len(document_types) == EXPECTED_DOCUMENT_TYPE_COUNT
        implemented_type_ids = [
            document_type.document_type_id
            for document_type in document_types
            if document_type.implemented
        ]
        # Order follows DOCUMENT_TYPE_SPECS: identity, then property (EC now real),
        # then the clearance NOC, then the four land documents.
        assert implemented_type_ids == [
            DocumentTypeEnum.AADHAAR.value,
            DocumentTypeEnum.PAN.value,
            DocumentTypeEnum.DRIVING_LICENCE.value,
            DocumentTypeEnum.SALE_DEED.value,
            DocumentTypeEnum.LINK_DOCUMENT.value,
            DocumentTypeEnum.ENCUMBRANCE_CERTIFICATE.value,
            DocumentTypeEnum.IRRIGATION_NOC.value,
            DocumentTypeEnum.CONVERSION_CERT.value,
            DocumentTypeEnum.MARKET_VALUE_CERT.value,
            DocumentTypeEnum.PATTADAR_PASSBOOK.value,
            DocumentTypeEnum.ORC.value,
        ]

    def test_the_encumbrance_certificate_is_now_implemented_and_manual_only(
        self, storage
    ):
        # Act — declared against IGRS, shipped manual-only for now (ADR-012)
        ec = storage.get_document_type(
            document_type_id=DocumentTypeEnum.ENCUMBRANCE_CERTIFICATE.value
        )

        # Assert
        assert ec.implemented is True
        assert ec.issuer_service_id is None
        assert ec.label == "Encumbrance certificate"

    def test_the_four_land_documents_are_implemented_with_no_department_to_ask(
        self, storage
    ):
        # Act
        land_type_ids = [
            DocumentTypeEnum.CONVERSION_CERT.value,
            DocumentTypeEnum.MARKET_VALUE_CERT.value,
            DocumentTypeEnum.PATTADAR_PASSBOOK.value,
            DocumentTypeEnum.ORC.value,
        ]

        # Assert — every revenue-side document settles by the officer's hand
        for document_type_id in land_type_ids:
            document_type = storage.get_document_type(document_type_id=document_type_id)
            assert document_type.implemented is True
            assert document_type.issuer_service_id is None

    def test_the_land_documents_carry_their_inferred_fields(self, storage):
        # Act
        conversion = storage.get_document_type(
            document_type_id=DocumentTypeEnum.CONVERSION_CERT.value
        )
        pattadar = storage.get_document_type(
            document_type_id=DocumentTypeEnum.PATTADAR_PASSBOOK.value
        )

        # Assert — the keys the read modules and sample reads have to match
        assert [field.key for field in conversion.field_specs] == [
            "conversionOrderNo",
            "issuedBy",
            "issueDate",
            "applicant",
            "surveyNo",
            "village",
            "extent",
            "convertedUse",
            "nalaAssessment",
        ]
        assert [field.key for field in pattadar.field_specs] == [
            "passbookNo",
            "pattadar",
            "khataNo",
            "surveyNo",
            "village",
            "extent",
            "landClassification",
            "issueDate",
        ]

    def test_the_irrigation_noc_is_implemented_with_no_department_to_ask(self, storage):
        # Act
        irrigation_noc = storage.get_document_type(
            document_type_id=DocumentTypeEnum.IRRIGATION_NOC.value
        )

        # Assert — the one implemented type whose department publishes no interface
        assert irrigation_noc.implemented is True
        assert irrigation_noc.issuer_service_id is None
        assert irrigation_noc.label == "Irrigation NOC"
        assert [field.key for field in irrigation_noc.field_specs] == [
            "nocNo",
            "issuedBy",
            "issueDate",
            "validUpto",
            "applicant",
            "surveyNo",
            "bufferCondition",
        ]
        assert [structure.key for structure in irrigation_noc.structure_specs] == [
            "seal",
            "signature",
        ]

    def test_get_document_type_for_pan_returns_the_four_prototype_fields(self, storage):
        # Act
        pan_type = storage.get_document_type(document_type_id=DocumentTypeEnum.PAN.value)

        # Assert
        assert pan_type.label == "PAN"
        assert pan_type.issuer_service_id == IssuerServiceEnum.ITD_PAN.value
        assert [field_spec.key for field_spec in pan_type.field_specs] == [
            "name",
            "parentName",
            "dob",
            "pan",
        ]
        assert [structure.key for structure in pan_type.structure_specs] == [
            "photo",
            "signature",
            "hologram",
        ]

    def test_get_document_type_order_excludes_the_unknown_type(self, storage):
        # Act
        document_type_order = storage.get_document_type_order()

        # Assert
        assert len(document_type_order) == EXPECTED_ORDERED_TYPE_COUNT
        assert DocumentTypeEnum.UNKNOWN.value not in document_type_order
        assert document_type_order[0] == DocumentTypeEnum.AADHAAR.value
        assert document_type_order[1] == DocumentTypeEnum.PAN.value

    def test_get_issuer_service_for_income_tax_returns_the_prototype_latency(self, storage):
        # Act
        issuer_service = storage.get_issuer_service(
            issuer_service_id=IssuerServiceEnum.ITD_PAN.value
        )

        # Assert
        assert issuer_service.name == "Income Tax PAN verification"
        assert issuer_service.latency_ms == 900
        assert issuer_service.endpoint == "POST /pan/verify"

    def test_get_filename_keyword_rules_preserves_first_match_wins_order(self, storage):
        # Act
        keyword_rules = storage.get_filename_keyword_rules()

        # Assert
        keywords = [rule.keyword for rule in keyword_rules]
        assert keywords.index("aadhaar") < keywords.index("pan")
        assert keywords.index("link") < keywords.index("sale")
        pan_rule = next(rule for rule in keyword_rules if rule.keyword == "pan")
        assert pan_rule.document_type_id == DocumentTypeEnum.PAN.value

    def test_get_document_types_returns_a_copy_the_caller_cannot_mutate(self, storage):
        # Arrange
        document_types = storage.get_document_types()

        # Act
        document_types.clear()

        # Assert
        assert len(storage.get_document_types()) == EXPECTED_DOCUMENT_TYPE_COUNT
