import pytest

from document_catalog.storages.reference_data.document_type_specs import (
    DOCUMENT_TYPE_SPECS,
)
from document_extraction.adapters.reads.document_read_registry import (
    READS_BY_DOCUMENT_TYPE,
    get_document_read,
    is_bundleable,
)
from document_extraction.exceptions.extraction_exceptions import (
    DocumentReadNotRegistered,
)

IMPLEMENTED_TYPE_IDS = tuple(
    document_type.document_type_id
    for document_type in DOCUMENT_TYPE_SPECS
    if document_type.implemented
)


class TestDocumentReadRegistry:
    @pytest.mark.parametrize("document_type_id", IMPLEMENTED_TYPE_IDS)
    def test_every_implemented_type_has_instructions_for_reading_it(
        self, document_type_id
    ):
        """The registry's own invariant, asserted rather than trusted.

        A type marked implemented in the catalog with no read registered would be
        reported to the officer as an unreadable scan, which blames the document for
        a wiring mistake.
        """
        # Act
        read_spec = get_document_read(document_type_id=document_type_id)

        # Assert
        assert read_spec.document_type_id == document_type_id
        assert read_spec.prompt.strip() != ""

    @pytest.mark.parametrize("document_type_id", IMPLEMENTED_TYPE_IDS)
    def test_every_read_maps_only_keys_its_catalog_entry_declares(
        self, document_type_id
    ):
        # Arrange — a read that emitted a key the catalog does not know would produce
        # a value no check could ever look at
        document_type = next(
            spec
            for spec in DOCUMENT_TYPE_SPECS
            if spec.document_type_id == document_type_id
        )
        declared_field_keys = {field.key for field in document_type.field_specs}
        declared_structure_keys = {
            structure.key for structure in document_type.structure_specs
        }

        # Act
        read_spec = get_document_read(document_type_id=document_type_id)

        # Assert
        assert set(read_spec.field_keys_by_attribute.values()) <= declared_field_keys
        assert (
            set(read_spec.structure_keys_by_attribute.values())
            <= declared_structure_keys
        )

    def test_a_type_this_build_cannot_read_is_reported_as_a_wiring_mistake(self):
        # Act & Assert — never a silent fall-through to another type's prompt
        with pytest.raises(DocumentReadNotRegistered) as raised:
            get_document_read(document_type_id="tax_receipt")
        assert raised.value.document_type_id == "tax_receipt"

    def test_only_the_deed_types_are_worth_looking_inside(self):
        # Act
        bundleable = {
            document_type_id
            for document_type_id in READS_BY_DOCUMENT_TYPE
            if is_bundleable(document_type_id=document_type_id)
        }

        # Assert — a clearance letter is one letter, never a file of many
        assert bundleable == {"sale_deed", "link_doc"}
        assert is_bundleable(document_type_id="irrigation_noc") is False
