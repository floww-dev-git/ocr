import dataclasses

import pytest

from document_scrutiny.constants.enums import CheckGroup, CheckStatus
from document_scrutiny.dtos.officer_action_dtos import UpdateDocumentFieldRequestDTO
from document_scrutiny.dtos.thread_dtos import ScrutinyThreadDTO
from document_scrutiny.exceptions.scrutiny_exceptions import DocumentFieldNotFound
from document_scrutiny.tests.conftest import (
    SCRUTINY_TODAY,
    ALL_STRUCTURE_PRESENT,
    MISMATCH_APPLICATION_ID,
    ScrutinyStorageMock,
    build_pan_field_values,
)
from document_scrutiny.tests.factories.scrutiny_dto_factories import (
    CheckDTOFactory,
    DocumentStateDTOFactory,
)

THREAD_ID = "thread_1"
DOCUMENT_ID = "document_1"
MISREAD_NAME = "MOHAMMED IRFAN SIDDIQI"
CORRECTED_NAME = "MOHAMMED IRFAN SIDDIQUI"
NAME_CHECK_ID = f"{DOCUMENT_ID}:name"
ISSUER_CHECK_ID = f"{DOCUMENT_ID}:issuer"


def build_issuer_check():
    return CheckDTOFactory(
        check_id=ISSUER_CHECK_ID,
        document_id=DOCUMENT_ID,
        group=CheckGroup.EXTERNAL.value,
        status=CheckStatus.WARN.value,
        title="Income Tax PAN verification did not fully match",
    )


class TestUpdateDocumentFieldInteractor(ScrutinyStorageMock):
    @pytest.fixture
    def interactor(self, thread_storage, catalog_service):
        from document_scrutiny.interactors.update_document_field_interactor import (
            UpdateDocumentFieldInteractor,
        )

        return UpdateDocumentFieldInteractor(
            thread_storage=thread_storage,
            catalog_service=catalog_service,
            scrutiny_today=SCRUTINY_TODAY,
        )

    def _read_document(self, name: str = MISREAD_NAME, checks=()):
        return DocumentStateDTOFactory(
            document_id=DOCUMENT_ID,
            field_values=build_pan_field_values(
                name=name,
                parent_name="MOHAMMED YOUSUF SIDDIQUI",
                date_of_birth="1982-11-27",
                pan="BNMPS7720K",
            ),
            structure_findings=dict(ALL_STRUCTURE_PRESENT),
            checks=checks,
        )

    def _analyzed_document(self, name: str = MISREAD_NAME, extra_checks=()):
        """A document as the analyze run left it: read values plus the checks
        those values produced."""
        from document_scrutiny.interactors.run_document_checks_interactor import (
            RunDocumentChecksInteractor,
        )
        from document_scrutiny.tests.conftest import build_pan_checks_request

        document = self._read_document(name=name)
        checks = RunDocumentChecksInteractor().run_checks(
            request=build_pan_checks_request(
                application_id=MISMATCH_APPLICATION_ID,
                field_values=document.field_values,
            )
        )
        return dataclasses.replace(document, checks=tuple(checks) + tuple(extra_checks))

    def _arrange(self, thread_storage, document):
        thread_storage.get_thread.return_value = ScrutinyThreadDTO(
            thread_id=THREAD_ID,
            application_id=MISMATCH_APPLICATION_ID,
            documents=(document,),
        )
        thread_storage.get_document.return_value = document
        thread_storage.update_document.side_effect = (
            lambda update_document: update_document.document
        )

    def _edit(self, interactor, field_key: str = "name", value: str = CORRECTED_NAME):
        return interactor.update_field(
            request=UpdateDocumentFieldRequestDTO(
                thread_id=THREAD_ID,
                document_id=DOCUMENT_ID,
                field_key=field_key,
                value=value,
            )
        )

    def test_the_officers_correction_replaces_what_the_machine_read(
        self, interactor, thread_storage
    ):
        # Arrange
        self._arrange(thread_storage, self._read_document())

        # Act
        change = self._edit(interactor)

        # Assert
        name_field = next(
            value for value in change.document.field_values if value.key == "name"
        )
        assert name_field.value == CORRECTED_NAME
        assert name_field.edited is True

    def test_a_field_the_document_does_not_have_cannot_be_edited(
        self, interactor, thread_storage
    ):
        # Arrange
        self._arrange(thread_storage, self._read_document())

        # Act & Assert
        with pytest.raises(DocumentFieldNotFound) as raised:
            self._edit(interactor, field_key="passportNo", value="Z1234567")

        assert raised.value.field_key == "passportNo"
        thread_storage.update_document.assert_not_called()

    def test_only_the_named_field_is_touched(self, interactor, thread_storage):
        # Arrange
        document = self._read_document()
        self._arrange(thread_storage, document)

        # Act
        change = self._edit(interactor)

        # Assert
        untouched = [
            value for value in change.document.field_values if value.key != "name"
        ]
        assert untouched == [
            value for value in document.field_values if value.key != "name"
        ]

    def test_an_edit_withdraws_the_officers_earlier_sign_off(
        self, interactor, thread_storage
    ):
        # Arrange
        document = self._read_document()
        signed_off = dataclasses.replace(
            document,
            confirmed=True,
            field_values=tuple(
                dataclasses.replace(value, confirmed=True)
                for value in document.field_values
            ),
        )
        self._arrange(thread_storage, signed_off)

        # Act
        change = self._edit(interactor)

        # Assert
        assert change.document.confirmed is False
        edited_field = next(
            value for value in change.document.field_values if value.key == "name"
        )
        assert edited_field.confirmed is False

    def test_correcting_the_read_name_settles_the_name_check(
        self, interactor, thread_storage
    ):
        # Arrange
        self._arrange(thread_storage, self._analyzed_document())

        # Act
        change = self._edit(interactor)

        # Assert
        name_check = next(
            check for check in change.document.checks if check.check_id == NAME_CHECK_ID
        )
        assert name_check.status == CheckStatus.PASS.value
        assert change.changed_check_ids == (NAME_CHECK_ID,)

    def test_a_check_that_did_not_move_is_not_announced_as_changed(
        self, interactor, thread_storage
    ):
        # Arrange
        self._arrange(thread_storage, self._analyzed_document(name=CORRECTED_NAME))

        # Act
        change = self._edit(interactor, field_key="pan", value="BNMPS7720K")

        # Assert
        assert change.changed_check_ids == ()

    def test_the_departments_answer_is_not_rewritten_by_an_officers_edit(
        self, interactor, thread_storage
    ):
        # Arrange
        issuer_check = build_issuer_check()
        self._arrange(
            thread_storage, self._analyzed_document(extra_checks=(issuer_check,))
        )

        # Act
        change = self._edit(interactor)

        # Assert
        assert (
            next(
                check
                for check in change.document.checks
                if check.check_id == ISSUER_CHECK_ID
            )
            == issuer_check
        )

    def test_the_edit_is_handed_to_storage_under_the_right_thread(
        self, interactor, thread_storage
    ):
        # Arrange
        self._arrange(thread_storage, self._read_document())

        # Act
        self._edit(interactor)

        # Assert
        update = thread_storage.update_document.call_args.kwargs["update_document"]
        assert update.thread_id == THREAD_ID
        assert update.document.document_id == DOCUMENT_ID
