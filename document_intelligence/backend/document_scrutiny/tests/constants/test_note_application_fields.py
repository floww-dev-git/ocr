from document_catalog.app_interfaces.catalog_service_interface import (
    CatalogServiceInterface,
)
from document_scrutiny.constants.note_application_fields import NoteApplicationField
from document_scrutiny.tests.conftest import MISMATCH_APPLICATION_ID


class TestNoteApplicationFieldsContract:
    """Pins this app's restated vocabulary against the catalog's published data,
    so a renamed application field fails here rather than silently rendering "?"
    in an official note."""

    def test_every_field_the_note_describes_exists_on_a_real_application(self):
        # Arrange
        catalog_service = CatalogServiceInterface()

        # Act
        available = set(
            catalog_service.get_application(
                application_id=MISMATCH_APPLICATION_ID
            ).field_values
        )

        # Assert
        missing = {
            field.value
            for field in NoteApplicationField
            if field.value not in available
        }
        assert missing == set()
