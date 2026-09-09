import dataclasses
import json

import pytest
from django.test import Client
from django.urls import reverse

from document_scrutiny.constants.enums import (
    CheckGroup,
    CheckResolution,
    CheckStatus,
    DocumentStage,
    DocumentStatus,
    ThreadStatus,
)
from document_scrutiny.dtos.thread_dtos import (
    AddDocumentsToThreadDTO,
    CreateScrutinyThreadDTO,
    StoredFileDTO,
    UpdateDocumentDTO,
)
from document_scrutiny.storages.in_memory_scrutiny_thread_storage import (
    InMemoryScrutinyThreadStorage,
)
from document_scrutiny.tests.conftest import (
    ALL_STRUCTURE_PRESENT,
    MISMATCH_APPLICATION_ID,
    build_pan_field_values,
)
from document_scrutiny.tests.factories.scrutiny_dto_factories import CheckDTOFactory

MISREAD_NAME = "MOHAMMED IRFAN SIDDIQI"
CORRECTED_NAME = "MOHAMMED IRFAN SIDDIQUI"
JSON_CONTENT_TYPE = "application/json"


@pytest.fixture
def client():
    return Client()


@pytest.fixture
def storage():
    return InMemoryScrutinyThreadStorage()


@pytest.fixture
def analyzed_thread(storage):
    """A thread as the analyze run leaves it for application 0377: one PAN whose
    name was misread, and an issuer answer that did not fully match."""
    from document_scrutiny.interactors.run_document_checks_interactor import (
        RunDocumentChecksInteractor,
    )
    from document_scrutiny.tests.conftest import build_pan_checks_request

    thread = storage.create_thread(
        create_thread=CreateScrutinyThreadDTO(application_id=MISMATCH_APPLICATION_ID)
    )
    documents = storage.add_documents(
        add_documents=AddDocumentsToThreadDTO(
            thread_id=thread.thread_id,
            stored_files=(
                StoredFileDTO(
                    filename="pan_card.jpg",
                    file_format="JPG",
                    file_size_bytes=188_000,
                    stored_path="/tmp/pan_card.jpg",
                ),
            ),
        )
    )
    document_id = documents[0].document_id
    field_values = build_pan_field_values(
        name=MISREAD_NAME,
        parent_name="MOHAMMED YOUSUF SIDDIQUI",
        date_of_birth="1982-11-27",
        pan="BNMPS7720K",
    )
    checks = RunDocumentChecksInteractor().run_checks(
        request=dataclasses.replace(
            build_pan_checks_request(
                application_id=MISMATCH_APPLICATION_ID, field_values=field_values
            ),
            document_id=document_id,
        )
    )
    issuer_check = CheckDTOFactory(
        check_id=f"{document_id}:issuer",
        document_id=document_id,
        group=CheckGroup.EXTERNAL.value,
        status=CheckStatus.WARN.value,
        title="Income Tax PAN verification did not fully match",
        detail="The department holds this PAN but its record does not agree on the name.",
    )
    storage.update_document(
        update_document=UpdateDocumentDTO(
            thread_id=thread.thread_id,
            document=dataclasses.replace(
                documents[0],
                document_type_id="pan",
                document_type_label="PAN",
                stage=DocumentStage.DONE.value,
                implemented=True,
                page_count=1,
                field_values=field_values,
                structure_findings=dict(ALL_STRUCTURE_PRESENT),
                checks=tuple(checks) + (issuer_check,),
            ),
        )
    )
    return thread.thread_id, document_id


def field_url(thread_id: str, document_id: str, field_key: str) -> str:
    return reverse(
        "update_document_field",
        kwargs={
            "thread_id": thread_id,
            "document_id": document_id,
            "field_key": field_key,
        },
    )


class TestUpdateDocumentField:
    def test_a_correction_is_accepted_and_the_check_settles(
        self, client, analyzed_thread
    ):
        # Arrange
        thread_id, document_id = analyzed_thread

        # Act
        response = client.patch(
            field_url(thread_id, document_id, "name"),
            data=json.dumps({"value": CORRECTED_NAME}),
            content_type=JSON_CONTENT_TYPE,
        )

        # Assert
        assert response.status_code == 200
        body = response.json()
        assert body["changedCheckIds"] == [f"{document_id}:name"]
        name_check = next(
            check
            for check in body["document"]["checks"]
            if check["checkId"] == f"{document_id}:name"
        )
        assert name_check["status"] == CheckStatus.PASS.value

    def test_the_thread_still_needs_attention_while_the_department_disagrees(
        self, client, analyzed_thread
    ):
        # Arrange
        thread_id, document_id = analyzed_thread

        # Act
        response = client.patch(
            field_url(thread_id, document_id, "name"),
            data=json.dumps({"value": CORRECTED_NAME}),
            content_type=JSON_CONTENT_TYPE,
        )

        # Assert
        summary = response.json()["summary"]
        assert summary["threadStatus"] == ThreadStatus.ATTENTION.value
        assert [item["checkId"] for item in summary["openItems"]] == [
            f"{document_id}:issuer"
        ]

    def test_a_field_the_document_does_not_have_is_reported_as_missing(
        self, client, analyzed_thread
    ):
        # Arrange
        thread_id, document_id = analyzed_thread

        # Act
        response = client.patch(
            field_url(thread_id, document_id, "passportNo"),
            data=json.dumps({"value": "Z1234567"}),
            content_type=JSON_CONTENT_TYPE,
        )

        # Assert
        assert response.status_code == 404
        assert response.json()["errorCode"] == "DOCUMENT_FIELD_NOT_FOUND"

    def test_an_edit_without_a_value_is_refused(self, client, analyzed_thread):
        # Arrange
        thread_id, document_id = analyzed_thread

        # Act
        response = client.patch(
            field_url(thread_id, document_id, "name"),
            data=json.dumps({}),
            content_type=JSON_CONTENT_TYPE,
        )

        # Assert
        assert response.status_code == 400
        assert response.json()["errorCode"] == "FIELD_VALUE_REQUIRED"

    def test_an_edit_on_a_thread_nobody_opened_is_reported_as_missing(self, client):
        # Act
        response = client.patch(
            field_url("thread_missing", "document_1", "name"),
            data=json.dumps({"value": CORRECTED_NAME}),
            content_type=JSON_CONTENT_TYPE,
        )

        # Assert
        assert response.status_code == 404
        assert response.json()["errorCode"] == "THREAD_NOT_FOUND"

    def test_the_wrong_method_is_rejected(self, client, analyzed_thread):
        # Arrange
        thread_id, document_id = analyzed_thread

        # Act
        response = client.get(field_url(thread_id, document_id, "name"))

        # Assert
        assert response.status_code == 405


class TestConfirmDocumentFields:
    def test_signing_off_confirms_the_document(self, client, analyzed_thread):
        # Arrange
        thread_id, document_id = analyzed_thread

        # Act
        response = client.post(
            reverse(
                "confirm_document_fields",
                kwargs={"thread_id": thread_id, "document_id": document_id},
            )
        )

        # Assert
        assert response.status_code == 200
        body = response.json()
        assert body["document"]["confirmed"] is True
        assert body["summary"]["confirmedDocumentCount"] == 1

    def test_signing_off_a_document_that_is_not_there_is_reported_as_missing(
        self, client, analyzed_thread
    ):
        # Arrange
        thread_id, _ = analyzed_thread

        # Act
        response = client.post(
            reverse(
                "confirm_document_fields",
                kwargs={"thread_id": thread_id, "document_id": "document_missing"},
            )
        )

        # Assert
        assert response.status_code == 404
        assert response.json()["errorCode"] == "DOCUMENT_NOT_FOUND"


class TestResolveCheck:
    def _resolve(self, client, thread_id: str, check_id: str, action: str):
        return client.post(
            reverse(
                "resolve_check", kwargs={"thread_id": thread_id, "check_id": check_id}
            ),
            data=json.dumps({"action": action}),
            content_type=JSON_CONTENT_TYPE,
        )

    def test_marking_the_issuer_answer_verified_by_hand_clears_the_thread(
        self, client, analyzed_thread
    ):
        # Arrange
        thread_id, document_id = analyzed_thread
        client.patch(
            field_url(thread_id, document_id, "name"),
            data=json.dumps({"value": CORRECTED_NAME}),
            content_type=JSON_CONTENT_TYPE,
        )

        # Act
        response = self._resolve(
            client,
            thread_id,
            f"{document_id}:issuer",
            CheckResolution.MANUAL.value,
        )

        # Assert
        assert response.status_code == 200
        body = response.json()
        assert body["check"]["manual"] is True
        assert body["check"]["status"] == CheckStatus.WARN.value
        assert body["summary"]["threadStatus"] == ThreadStatus.CLEAR.value
        assert body["summary"]["openItems"] == []

    def test_a_check_this_thread_does_not_have_is_reported_as_missing(
        self, client, analyzed_thread
    ):
        # Arrange
        thread_id, _ = analyzed_thread

        # Act
        response = self._resolve(
            client, thread_id, "document_9:name", CheckResolution.ACKNOWLEDGED.value
        )

        # Assert
        assert response.status_code == 404
        assert response.json()["errorCode"] == "CHECK_NOT_FOUND"

    def test_an_action_the_system_does_not_offer_is_refused(
        self, client, analyzed_thread
    ):
        # Arrange
        thread_id, document_id = analyzed_thread

        # Act
        response = self._resolve(client, thread_id, f"{document_id}:issuer", "waived")

        # Assert
        assert response.status_code == 400
        assert response.json()["errorCode"] == "UNKNOWN_CHECK_RESOLUTION"


class TestRetryIssuerVerification:
    def _retry(self, client, thread_id: str, document_id: str):
        return client.post(
            reverse(
                "retry_issuer_verification",
                kwargs={"thread_id": thread_id, "document_id": document_id},
            )
        )

    def test_a_department_that_already_agreed_is_not_asked_again(
        self, client, analyzed_thread, storage
    ):
        # Arrange
        thread_id, document_id = analyzed_thread
        document = storage.get_document(
            lookup=_lookup(thread_id=thread_id, document_id=document_id)
        )
        storage.update_document(
            update_document=UpdateDocumentDTO(
                thread_id=thread_id,
                document=dataclasses.replace(
                    document,
                    checks=tuple(
                        dataclasses.replace(check, status=CheckStatus.PASS.value)
                        if check.group == CheckGroup.EXTERNAL.value
                        else check
                        for check in document.checks
                    ),
                ),
            )
        )

        # Act
        response = self._retry(client, thread_id, document_id)

        # Assert
        assert response.status_code == 400
        assert response.json()["errorCode"] == "CHECK_NOT_RETRYABLE"

    def test_a_document_never_sent_for_verification_cannot_be_retried(
        self, client, analyzed_thread, storage
    ):
        # Arrange
        thread_id, document_id = analyzed_thread
        document = storage.get_document(
            lookup=_lookup(thread_id=thread_id, document_id=document_id)
        )
        storage.update_document(
            update_document=UpdateDocumentDTO(
                thread_id=thread_id,
                document=dataclasses.replace(
                    document,
                    checks=tuple(
                        check
                        for check in document.checks
                        if check.group != CheckGroup.EXTERNAL.value
                    ),
                ),
            )
        )

        # Act
        response = self._retry(client, thread_id, document_id)

        # Assert
        assert response.status_code == 404
        assert response.json()["errorCode"] == "ISSUER_CHECK_MISSING"


class TestUpdateServiceOverrides:
    def test_a_forced_answer_is_recorded_on_the_thread(self, client, analyzed_thread):
        # Arrange
        thread_id, _ = analyzed_thread

        # Act
        response = client.put(
            reverse("update_service_overrides", kwargs={"thread_id": thread_id}),
            data=json.dumps({"serviceOverrides": {"itd_pan": "timeout"}}),
            content_type=JSON_CONTENT_TYPE,
        )

        # Assert
        assert response.status_code == 200
        assert response.json()["serviceOverrides"] == {"itd_pan": "timeout"}

    def test_overrides_for_a_thread_nobody_opened_are_reported_as_missing(self, client):
        # Act
        response = client.put(
            reverse("update_service_overrides", kwargs={"thread_id": "thread_missing"}),
            data=json.dumps({"serviceOverrides": {}}),
            content_type=JSON_CONTENT_TYPE,
        )

        # Assert
        assert response.status_code == 404
        assert response.json()["errorCode"] == "THREAD_NOT_FOUND"

    def test_overrides_that_are_not_a_mapping_are_refused(
        self, client, analyzed_thread
    ):
        # Arrange
        thread_id, _ = analyzed_thread

        # Act
        response = client.put(
            reverse("update_service_overrides", kwargs={"thread_id": thread_id}),
            data=json.dumps({"serviceOverrides": ["timeout"]}),
            content_type=JSON_CONTENT_TYPE,
        )

        # Assert
        assert response.status_code == 400
        assert response.json()["errorCode"] == "INVALID_SERVICE_OVERRIDES"


class TestGetScrutinyNote:
    def test_the_note_reports_what_is_still_open(self, client, analyzed_thread):
        # Arrange
        thread_id, document_id = analyzed_thread

        # Act
        response = client.get(
            reverse("get_scrutiny_note", kwargs={"thread_id": thread_id})
        )

        # Assert
        assert response.status_code == 200
        text = response.json()["text"]
        assert MISMATCH_APPLICATION_ID in text
        assert "Open: PAN: Name matches application" in text
        assert "Raise shortfall" in text

    def test_the_note_turns_favourable_once_everything_is_settled(
        self, client, analyzed_thread
    ):
        # Arrange
        thread_id, document_id = analyzed_thread
        client.patch(
            field_url(thread_id, document_id, "name"),
            data=json.dumps({"value": CORRECTED_NAME}),
            content_type=JSON_CONTENT_TYPE,
        )
        client.post(
            reverse(
                "resolve_check",
                kwargs={"thread_id": thread_id, "check_id": f"{document_id}:issuer"},
            ),
            data=json.dumps({"action": CheckResolution.MANUAL.value}),
            content_type=JSON_CONTENT_TYPE,
        )

        # Act
        response = client.get(
            reverse("get_scrutiny_note", kwargs={"thread_id": thread_id})
        )

        # Assert
        text = response.json()["text"]
        assert "Fit to proceed" in text
        assert "Open:" not in text

    def test_a_note_for_a_thread_nobody_opened_is_reported_as_missing(self, client):
        # Act
        response = client.get(
            reverse("get_scrutiny_note", kwargs={"thread_id": "thread_missing"})
        )

        # Assert
        assert response.status_code == 404
        assert response.json()["errorCode"] == "THREAD_NOT_FOUND"


def _lookup(thread_id: str, document_id: str):
    from document_scrutiny.dtos.thread_dtos import DocumentLookupDTO

    return DocumentLookupDTO(thread_id=thread_id, document_id=document_id)


class TestOfficerActionsWhileTheDocumentIsBeingRead:
    """The analyze run works from the document it read at the start, so an action
    accepted mid-run would be reported as saved and then overwritten."""

    @pytest.fixture
    def mid_run_thread(self, storage, analyzed_thread):
        thread_id, document_id = analyzed_thread
        document = storage.get_document(
            lookup=_lookup(thread_id=thread_id, document_id=document_id)
        )
        storage.update_document(
            update_document=UpdateDocumentDTO(
                thread_id=thread_id,
                document=dataclasses.replace(
                    document, stage=DocumentStage.VERIFYING.value
                ),
            )
        )
        return thread_id, document_id

    def test_an_edit_is_refused_rather_than_silently_lost(self, client, mid_run_thread):
        # Arrange
        thread_id, document_id = mid_run_thread

        # Act
        response = client.patch(
            field_url(thread_id, document_id, "name"),
            data=json.dumps({"value": CORRECTED_NAME}),
            content_type=JSON_CONTENT_TYPE,
        )

        # Assert
        assert response.status_code == 409
        assert response.json()["errorCode"] == "DOCUMENT_BUSY"

    def test_the_refused_edit_left_the_read_value_untouched(
        self, client, mid_run_thread, storage
    ):
        # Arrange
        thread_id, document_id = mid_run_thread

        # Act
        client.patch(
            field_url(thread_id, document_id, "name"),
            data=json.dumps({"value": CORRECTED_NAME}),
            content_type=JSON_CONTENT_TYPE,
        )

        # Assert
        document = storage.get_document(
            lookup=_lookup(thread_id=thread_id, document_id=document_id)
        )
        name = next(
            value for value in document.field_values if value.key == "name"
        )
        assert name.value == MISREAD_NAME
        assert name.edited is False

    def test_signing_off_is_refused_mid_run(self, client, mid_run_thread):
        # Arrange
        thread_id, document_id = mid_run_thread

        # Act
        response = client.post(
            reverse(
                "confirm_document_fields",
                kwargs={"thread_id": thread_id, "document_id": document_id},
            )
        )

        # Assert
        assert response.status_code == 409
        assert response.json()["errorCode"] == "DOCUMENT_BUSY"

    def test_resolving_a_check_is_refused_mid_run(self, client, mid_run_thread):
        # Arrange
        thread_id, document_id = mid_run_thread

        # Act
        response = client.post(
            reverse(
                "resolve_check",
                kwargs={"thread_id": thread_id, "check_id": f"{document_id}:issuer"},
            ),
            data=json.dumps({"action": CheckResolution.MANUAL.value}),
            content_type=JSON_CONTENT_TYPE,
        )

        # Assert
        assert response.status_code == 409
        assert response.json()["errorCode"] == "DOCUMENT_BUSY"

    def test_retrying_verification_is_refused_mid_run(self, client, mid_run_thread):
        # Arrange
        thread_id, document_id = mid_run_thread

        # Act
        response = client.post(
            reverse(
                "retry_issuer_verification",
                kwargs={"thread_id": thread_id, "document_id": document_id},
            )
        )

        # Assert
        assert response.status_code == 409
        assert response.json()["errorCode"] == "DOCUMENT_BUSY"


class TestFieldValueValidation:
    @pytest.mark.parametrize(
        "value", [None, 12345, True, {"a": 1}, ["x"]], ids=str
    )
    def test_a_value_that_is_not_text_is_refused(
        self, client, analyzed_thread, value
    ):
        # Arrange
        thread_id, document_id = analyzed_thread

        # Act
        response = client.patch(
            field_url(thread_id, document_id, "name"),
            data=json.dumps({"value": value}),
            content_type=JSON_CONTENT_TYPE,
        )

        # Assert
        assert response.status_code == 400
        assert response.json()["errorCode"] == "FIELD_VALUE_NOT_TEXT"

    def test_a_python_repr_never_reaches_the_officers_record(
        self, client, analyzed_thread, storage
    ):
        # Arrange
        thread_id, document_id = analyzed_thread

        # Act
        client.patch(
            field_url(thread_id, document_id, "name"),
            data=json.dumps({"value": None}),
            content_type=JSON_CONTENT_TYPE,
        )

        # Assert
        document = storage.get_document(
            lookup=_lookup(thread_id=thread_id, document_id=document_id)
        )
        name = next(value for value in document.field_values if value.key == "name")
        assert name.value == MISREAD_NAME

    def test_an_unbounded_value_is_refused(self, client, analyzed_thread):
        # Arrange
        thread_id, document_id = analyzed_thread

        # Act
        response = client.patch(
            field_url(thread_id, document_id, "name"),
            data=json.dumps({"value": "A" * 100_000}),
            content_type=JSON_CONTENT_TYPE,
        )

        # Assert
        assert response.status_code == 400
        assert response.json()["errorCode"] == "FIELD_VALUE_TOO_LONG"

    def test_clearing_a_field_is_accepted_and_keeps_the_item_on_the_worklist(
        self, client, analyzed_thread
    ):
        # Arrange
        thread_id, document_id = analyzed_thread

        # Act
        response = client.patch(
            field_url(thread_id, document_id, "pan"),
            data=json.dumps({"value": ""}),
            content_type=JSON_CONTENT_TYPE,
        )

        # Assert
        assert response.status_code == 200
        body = response.json()
        pan_check = next(
            check
            for check in body["document"]["checks"]
            if check["checkId"] == f"{document_id}:pan"
        )
        assert pan_check["status"] == CheckStatus.WARN.value
        assert "cleared by the officer" in pan_check["title"]
        assert f"{document_id}:pan" in body["changedCheckIds"]


class TestConfirmPreconditions:
    def test_a_document_nobody_read_cannot_be_signed_off(self, client, storage):
        # Arrange
        thread = storage.create_thread(
            create_thread=CreateScrutinyThreadDTO(
                application_id=MISMATCH_APPLICATION_ID
            )
        )
        documents = storage.add_documents(
            add_documents=AddDocumentsToThreadDTO(
                thread_id=thread.thread_id,
                stored_files=(
                    StoredFileDTO(
                        filename="pan_card.jpg",
                        file_format="JPG",
                        file_size_bytes=1024,
                        stored_path="/tmp/pan_card.jpg",
                    ),
                ),
            )
        )

        # Act
        response = client.post(
            reverse(
                "confirm_document_fields",
                kwargs={
                    "thread_id": thread.thread_id,
                    "document_id": documents[0].document_id,
                },
            )
        )

        # Assert
        assert response.status_code == 400
        assert response.json()["errorCode"] == "NOTHING_TO_CONFIRM"


class TestDerivedDocumentStatus:
    def test_the_document_and_the_thread_never_disagree_after_a_resolution(
        self, client, analyzed_thread
    ):
        # Arrange
        thread_id, document_id = analyzed_thread

        # Act — settle both open items
        client.post(
            reverse(
                "resolve_check",
                kwargs={"thread_id": thread_id, "check_id": f"{document_id}:name"},
            ),
            data=json.dumps({"action": CheckResolution.ACKNOWLEDGED.value}),
            content_type=JSON_CONTENT_TYPE,
        )
        response = client.post(
            reverse(
                "resolve_check",
                kwargs={"thread_id": thread_id, "check_id": f"{document_id}:issuer"},
            ),
            data=json.dumps({"action": CheckResolution.MANUAL.value}),
            content_type=JSON_CONTENT_TYPE,
        )

        # Assert
        body = response.json()
        assert body["summary"]["threadStatus"] == ThreadStatus.CLEAR.value
        assert body["document"]["status"] == DocumentStatus.VERIFIED.value

    def test_the_persisted_document_agrees_with_what_the_officer_was_shown(
        self, client, analyzed_thread
    ):
        # Arrange
        thread_id, document_id = analyzed_thread
        for check_key, action in (
            ("name", CheckResolution.ACKNOWLEDGED.value),
            ("issuer", CheckResolution.MANUAL.value),
        ):
            client.post(
                reverse(
                    "resolve_check",
                    kwargs={
                        "thread_id": thread_id,
                        "check_id": f"{document_id}:{check_key}",
                    },
                ),
                data=json.dumps({"action": action}),
                content_type=JSON_CONTENT_TYPE,
            )

        # Act
        response = client.get(
            reverse("get_scrutiny_thread", kwargs={"thread_id": thread_id})
        )

        # Assert
        document = response.json()["documents"][0]
        assert document["status"] == DocumentStatus.VERIFIED.value

    def test_a_note_on_an_unread_thread_recommends_nothing(self, client, storage):
        # Arrange
        thread = storage.create_thread(
            create_thread=CreateScrutinyThreadDTO(
                application_id=MISMATCH_APPLICATION_ID
            )
        )

        # Act
        response = client.get(
            reverse("get_scrutiny_note", kwargs={"thread_id": thread.thread_id})
        )

        # Assert
        text = response.json()["text"]
        assert "Fit to proceed" not in text
        assert "No recommendation yet" in text
