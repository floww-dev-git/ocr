import dataclasses

import pytest

from document_scrutiny.constants.enums import CheckGroup, CheckStatus
from document_scrutiny.dtos.document_dtos import FieldValueDTO
from document_scrutiny.tests.conftest import (
    CLEAN_APPLICATION_ID,
    DOCUMENT_ID,
    MISMATCH_APPLICATION_ID,
    SECOND_APPLICATION_ID,
    build_aadhaar_checks_request,
    build_aadhaar_field_values,
    build_pan_checks_request,
    build_pan_field_values,
    get_seeded_application,
)

# PAN gains an intrinsic date-of-birth consistency check on top of its eight.
EXPECTED_PAN_CHECK_COUNT = 9


class TestRunDocumentChecksInteractor:
    @pytest.fixture
    def interactor(self):
        from document_scrutiny.interactors.run_document_checks_interactor import (
            RunDocumentChecksInteractor,
        )

        return RunDocumentChecksInteractor()

    def _checks_by_id(self, checks):
        return {check.check_id: check for check in checks}

    def test_a_document_with_no_fields_read_produces_only_structure_checks(self, interactor):
        # Arrange
        request = build_pan_checks_request(field_values=())

        # Act
        checks = interactor.run_checks(request=request)

        # Assert
        assert [check.group for check in checks] == [CheckGroup.STRUCTURE.value] * 3

    def test_a_field_read_as_empty_produces_no_check_for_that_field(self, interactor):
        # Arrange
        request = build_pan_checks_request(
            field_values=(
                FieldValueDTO(key="name", value="", confidence=0.4),
                FieldValueDTO(key="pan", value="   ", confidence=0.4),
            )
        )

        # Act
        checks = interactor.run_checks(request=request)

        # Assert
        rule_checks = [check for check in checks if check.group == CheckGroup.RULE.value]
        assert rule_checks == []

    def test_a_missing_application_value_fails_and_says_the_application_reads_nothing(
        self, interactor
    ):
        # Arrange
        request = build_pan_checks_request()
        stripped_application = type(request.application)(
            application_id=request.application.application_id,
            status=request.application.status,
            field_values={**request.application.field_values, "parentName": ""},
        )
        request = dataclasses.replace(request, application=stripped_application)

        # Act
        checks = self._checks_by_id(interactor.run_checks(request=request))

        # Assert
        parent_check = checks[f"{DOCUMENT_ID}:parent"]
        assert parent_check.status == CheckStatus.FAIL.value
        assert "Application reads nothing." in parent_check.detail

    def test_a_pan_that_does_not_match_the_application_fails(self, interactor):
        # Arrange
        request = build_pan_checks_request(
            field_values=build_pan_field_values(
                name="SRINIVAS RAO KANDULA",
                parent_name="VENKATESWARA RAO KANDULA",
                date_of_birth="1979-08-14",
                pan="ZZZPZ9999Z",
            )
        )

        # Act
        checks = self._checks_by_id(interactor.run_checks(request=request))

        # Assert
        assert checks[f"{DOCUMENT_ID}:pan"].status == CheckStatus.FAIL.value
        assert checks[f"{DOCUMENT_ID}:pan-format"].status == CheckStatus.PASS.value

    def test_a_structurally_invalid_pan_fails_its_format_check(self, interactor):
        # Arrange
        request = build_pan_checks_request(
            field_values=build_pan_field_values(
                name="SRINIVAS RAO KANDULA",
                parent_name="VENKATESWARA RAO KANDULA",
                date_of_birth="1979-08-14",
                pan="DQRPK483",
            )
        )

        # Act
        checks = self._checks_by_id(interactor.run_checks(request=request))

        # Assert
        format_check = checks[f"{DOCUMENT_ID}:pan-format"]
        assert format_check.status == CheckStatus.FAIL.value
        assert format_check.detail == "A PAN is 10 characters; this one reads 8."

    def test_a_pan_with_an_unrecognised_holder_type_warns_on_format(self, interactor):
        # Arrange
        request = build_pan_checks_request(
            field_values=build_pan_field_values(
                name="SRINIVAS RAO KANDULA",
                parent_name="VENKATESWARA RAO KANDULA",
                date_of_birth="1979-08-14",
                pan="DQRZK4831L",
            )
        )

        # Act
        checks = self._checks_by_id(interactor.run_checks(request=request))

        # Assert
        assert checks[f"{DOCUMENT_ID}:pan-format"].status == CheckStatus.WARN.value

    def test_a_date_of_birth_that_differs_fails(self, interactor):
        # Arrange
        request = build_pan_checks_request(
            field_values=build_pan_field_values(
                name="SRINIVAS RAO KANDULA",
                parent_name="VENKATESWARA RAO KANDULA",
                date_of_birth="1978-08-14",
                pan="DQRPK4831L",
            )
        )

        # Act
        checks = self._checks_by_id(interactor.run_checks(request=request))

        # Assert
        date_check = checks[f"{DOCUMENT_ID}:dob"]
        assert date_check.status == CheckStatus.FAIL.value
        assert date_check.detail == (
            "PAN reads 14-08-1978. Application reads 14-08-1979."
        )

    def test_a_structure_element_that_was_not_detected_warns(self, interactor):
        # Arrange
        request = build_pan_checks_request(
            structure_findings={"photo": True, "signature": True, "hologram": False}
        )

        # Act
        checks = self._checks_by_id(interactor.run_checks(request=request))

        # Assert
        hologram_check = checks[f"{DOCUMENT_ID}:structure:hologram"]
        assert hologram_check.status == CheckStatus.WARN.value
        assert hologram_check.title == "Hologram not detected"

    def test_a_structure_element_absent_from_the_findings_is_not_asked_about(
        self, interactor
    ):
        """An element the read left out does not apply to this form of the document.

        An e-PAN is issued with no hologram, so the officer is told nothing about its
        hologram — neither that one is present, which would be false, nor that one is
        missing, which would be a warning about a feature never expected. Only an
        explicit false warns.
        """
        # Arrange
        request = build_pan_checks_request(structure_findings={})

        # Act
        checks = self._checks_by_id(interactor.run_checks(request=request))

        # Assert
        assert not [
            check_id for check_id in checks if ":structure:" in check_id
        ]

    def test_the_seeded_mismatch_application_warns_on_the_name_and_passes_the_rest(
        self, interactor
    ):
        # Arrange — AC2: the seeded PAN reads SIDDIQI against an application saying SIDDIQUI
        request = build_pan_checks_request(
            application_id=MISMATCH_APPLICATION_ID,
            field_values=build_pan_field_values(
                name="MOHAMMED IRFAN SIDDIQI",
                parent_name="MOHAMMED YOUSUF SIDDIQUI",
                date_of_birth="1982-11-27",
                pan="BNMPS7720K",
            ),
        )

        # Act
        checks = self._checks_by_id(interactor.run_checks(request=request))

        # Assert
        name_check = checks[f"{DOCUMENT_ID}:name"]
        assert name_check.status == CheckStatus.WARN.value
        assert name_check.detail == (
            "PAN reads MOHAMMED IRFAN SIDDIQI. "
            "Application reads Mohammed Irfan Siddiqui. Similarity 96%."
        )
        assert [
            check.status
            for check_id, check in checks.items()
            if check_id != f"{DOCUMENT_ID}:name"
        ] == [CheckStatus.PASS.value] * (EXPECTED_PAN_CHECK_COUNT - 1)

    def test_a_clean_application_passes_every_check(self, interactor):
        # Arrange — AC1
        request = build_pan_checks_request()

        # Act
        checks = interactor.run_checks(request=request)

        # Assert
        assert len(checks) == EXPECTED_PAN_CHECK_COUNT
        assert {check.status for check in checks} == {CheckStatus.PASS.value}
        assert [check.check_id for check in checks] == [
            f"{DOCUMENT_ID}:name",
            f"{DOCUMENT_ID}:parent",
            f"{DOCUMENT_ID}:dob",
            f"{DOCUMENT_ID}:pan",
            f"{DOCUMENT_ID}:pan-format",
            f"{DOCUMENT_ID}:structure:photo",
            f"{DOCUMENT_ID}:structure:signature",
            f"{DOCUMENT_ID}:structure:hologram",
            f"{DOCUMENT_ID}:internal-consistency",
        ]

    @pytest.mark.parametrize("noisy_pan", ["DQRPK 4831L", "dqrpk4831l", "DQRPK4831l"])
    def test_a_noisy_pan_matches_the_application_but_still_fails_its_format_check(
        self, interactor, noisy_pan
    ):
        # Arrange — the match rule is lenient ("same number?") where the format
        # rule is strict ("valid number?"), so one read can pass one and fail the other
        request = build_pan_checks_request(
            field_values=build_pan_field_values(
                name="SRINIVAS RAO KANDULA",
                parent_name="VENKATESWARA RAO KANDULA",
                date_of_birth="1979-08-14",
                pan=noisy_pan,
            )
        )

        # Act
        checks = self._checks_by_id(interactor.run_checks(request=request))

        # Assert
        assert checks[f"{DOCUMENT_ID}:pan"].status == CheckStatus.PASS.value
        assert checks[f"{DOCUMENT_ID}:pan-format"].status == CheckStatus.FAIL.value

    def test_punctuation_inside_a_pan_is_not_normalised_away(self, interactor):
        # Arrange — the prototype normalises whitespace and case only, so a
        # stray hyphen is a genuinely different number, not noise to absorb
        request = build_pan_checks_request(
            field_values=build_pan_field_values(
                name="SRINIVAS RAO KANDULA",
                parent_name="VENKATESWARA RAO KANDULA",
                date_of_birth="1979-08-14",
                pan="DQRPK-4831L",
            )
        )

        # Act
        checks = self._checks_by_id(interactor.run_checks(request=request))

        # Assert
        assert checks[f"{DOCUMENT_ID}:pan"].status == CheckStatus.FAIL.value
        assert checks[f"{DOCUMENT_ID}:pan-format"].status == CheckStatus.FAIL.value

    def test_a_pan_field_always_carries_both_a_match_and_a_format_check(self, interactor):
        # Arrange
        request = build_pan_checks_request()

        # Act
        checks = self._checks_by_id(interactor.run_checks(request=request))

        # Assert
        assert checks[f"{DOCUMENT_ID}:pan"].field_key == "pan"
        assert checks[f"{DOCUMENT_ID}:pan-format"].field_key == "pan"

    def test_every_check_carries_the_document_id_and_its_field_key(self, interactor):
        # Arrange
        request = build_pan_checks_request()

        # Act
        checks = interactor.run_checks(request=request)

        # Assert
        assert {check.document_id for check in checks} == {DOCUMENT_ID}
        # The field-keyed rule checks name the field they judge; the intrinsic ones
        # (the internal-consistency check) judge the document as a whole and carry no
        # field key, like the structure checks.
        rule_field_keys = {
            check.field_key
            for check in checks
            if check.group == CheckGroup.RULE.value and check.field_key is not None
        }
        assert rule_field_keys == {"name", "parentName", "dob", "pan"}
        structure_checks = [
            check for check in checks if check.group == CheckGroup.STRUCTURE.value
        ]
        assert all(check.field_key is None for check in structure_checks)


EXPECTED_AADHAAR_CHECK_COUNT = 10


class TestRunDocumentChecksInteractorForAadhaar:
    """The same engine over a second document type, with rules PAN never exercised."""

    @pytest.fixture
    def interactor(self):
        from document_scrutiny.interactors.run_document_checks_interactor import (
            RunDocumentChecksInteractor,
        )

        return RunDocumentChecksInteractor()

    def _checks_by_id(self, checks):
        return {check.check_id: check for check in checks}

    def test_an_aadhaar_agreeing_with_the_application_passes_every_check(
        self, interactor
    ):
        # Arrange — the second seeded application's card agrees throughout
        request = build_aadhaar_checks_request(
            application_id=SECOND_APPLICATION_ID
        )

        # Act
        checks = interactor.run_checks(request=request)

        # Assert
        assert len(checks) == EXPECTED_AADHAAR_CHECK_COUNT
        assert {check.status for check in checks} == {CheckStatus.PASS.value}

    def test_the_five_aadhaar_fields_each_get_their_own_check(self, interactor):
        # Arrange
        request = build_aadhaar_checks_request(
            application_id=SECOND_APPLICATION_ID
        )

        # Act
        checks = self._checks_by_id(interactor.run_checks(request=request))

        # Assert
        assert f"{DOCUMENT_ID}:name" in checks
        assert f"{DOCUMENT_ID}:dob" in checks
        assert f"{DOCUMENT_ID}:gender" in checks
        assert f"{DOCUMENT_ID}:aadhaar" in checks
        assert f"{DOCUMENT_ID}:address" in checks
        assert f"{DOCUMENT_ID}:aadhaar-format" in checks

    def test_an_aadhaar_carries_no_pan_check_and_a_pan_carries_no_aadhaar_check(
        self, interactor
    ):
        # Arrange — the format registry is per field, not per document
        aadhaar_checks = self._checks_by_id(
            interactor.run_checks(
                request=build_aadhaar_checks_request(
                    application_id=SECOND_APPLICATION_ID
                )
            )
        )
        pan_checks = self._checks_by_id(
            interactor.run_checks(request=build_pan_checks_request())
        )

        # Assert
        assert f"{DOCUMENT_ID}:pan-format" not in aadhaar_checks
        assert f"{DOCUMENT_ID}:aadhaar-format" not in pan_checks

    def test_the_seeded_moved_applicant_gets_a_warning_not_a_failure(self, interactor):
        # Arrange — the card carries the previous address, as the seeded read does.
        # An applicant who moved has not filed a false document.
        application = get_seeded_application(CLEAN_APPLICATION_ID)
        request = build_aadhaar_checks_request(
            application_id=CLEAN_APPLICATION_ID,
            field_values=build_aadhaar_field_values(
                name=application.field_values["applicantName"],
                date_of_birth=application.field_values["dob"],
                gender=application.field_values["gender"],
                aadhaar_number=application.field_values["aadhaarNo"],
                address=(
                    "H.No 8-2-293/82, Road No 12, Banjara Hills, Hyderabad 500034"
                ),
            ),
        )

        # Act
        checks = self._checks_by_id(interactor.run_checks(request=request))

        # Assert
        address_check = checks[f"{DOCUMENT_ID}:address"]
        assert address_check.status == CheckStatus.WARN.value
        assert "advisory" in address_check.detail
        assert address_check.field_key == "address"

    def test_a_disagreeing_gender_fails(self, interactor):
        # Arrange
        application = get_seeded_application(SECOND_APPLICATION_ID)
        request = build_aadhaar_checks_request(
            application_id=SECOND_APPLICATION_ID,
            field_values=build_aadhaar_field_values(
                name=application.field_values["applicantName"],
                date_of_birth=application.field_values["dob"],
                gender="Male",
                aadhaar_number=application.field_values["aadhaarNo"],
                address=application.field_values["address"],
            ),
        )

        # Act
        checks = self._checks_by_id(interactor.run_checks(request=request))

        # Assert
        gender_check = checks[f"{DOCUMENT_ID}:gender"]
        assert gender_check.status == CheckStatus.FAIL.value
        assert "reads Male" in gender_check.detail
        assert "Female" in gender_check.detail

    def test_a_gender_written_in_another_case_still_agrees(self, interactor):
        # Arrange
        application = get_seeded_application(SECOND_APPLICATION_ID)
        request = build_aadhaar_checks_request(
            application_id=SECOND_APPLICATION_ID,
            field_values=build_aadhaar_field_values(
                name=application.field_values["applicantName"],
                date_of_birth=application.field_values["dob"],
                gender="FEMALE",
                aadhaar_number=application.field_values["aadhaarNo"],
                address=application.field_values["address"],
            ),
        )

        # Act
        checks = self._checks_by_id(interactor.run_checks(request=request))

        # Assert
        assert checks[f"{DOCUMENT_ID}:gender"].status == CheckStatus.PASS.value

    def test_a_disagreeing_number_fails_and_is_masked_in_the_detail(self, interactor):
        # Arrange — the detail is copied into the permanent file
        application = get_seeded_application(SECOND_APPLICATION_ID)
        misread_number = "409322107755"
        request = build_aadhaar_checks_request(
            application_id=SECOND_APPLICATION_ID,
            field_values=build_aadhaar_field_values(
                name=application.field_values["applicantName"],
                date_of_birth=application.field_values["dob"],
                gender=application.field_values["gender"],
                aadhaar_number=misread_number,
                address=application.field_values["address"],
            ),
        )

        # Act
        checks = self._checks_by_id(interactor.run_checks(request=request))

        # Assert
        aadhaar_check = checks[f"{DOCUMENT_ID}:aadhaar"]
        assert aadhaar_check.status == CheckStatus.FAIL.value
        assert "XXXX XXXX 7755" in aadhaar_check.detail
        assert "XXXX XXXX 7754" in aadhaar_check.detail
        assert misread_number not in aadhaar_check.detail
        assert application.field_values["aadhaarNo"] not in aadhaar_check.detail

    def test_an_agreeing_number_is_masked_too(self, interactor):
        # Arrange
        request = build_aadhaar_checks_request(
            application_id=SECOND_APPLICATION_ID
        )

        # Act
        checks = self._checks_by_id(interactor.run_checks(request=request))

        # Assert
        aadhaar_check = checks[f"{DOCUMENT_ID}:aadhaar"]
        assert aadhaar_check.detail == "Both read XXXX XXXX 7754."

    def test_a_pan_is_never_masked_because_it_carries_no_such_convention(
        self, interactor
    ):
        # Arrange
        request = build_pan_checks_request()

        # Act
        checks = self._checks_by_id(interactor.run_checks(request=request))

        # Assert
        assert checks[f"{DOCUMENT_ID}:pan"].detail == "Both read DQRPK4831L."

    def test_a_structural_element_the_aadhaar_template_expects_but_lacks_warns(
        self, interactor
    ):
        # Arrange — AC5 over the second type
        request = build_aadhaar_checks_request(
            application_id=SECOND_APPLICATION_ID,
            structure_findings={"photo": True, "qr": False, "emblem": True},
        )

        # Act
        checks = self._checks_by_id(interactor.run_checks(request=request))

        # Assert
        qr_check = checks[f"{DOCUMENT_ID}:structure:qr"]
        assert qr_check.status == CheckStatus.WARN.value
        assert qr_check.title == "QR code not detected"

    def test_a_malformed_number_fails_its_format_check_without_the_application(
        self, interactor
    ):
        # Arrange — AC4 over the second type: no application context needed
        application = get_seeded_application(SECOND_APPLICATION_ID)
        request = build_aadhaar_checks_request(
            application_id=SECOND_APPLICATION_ID,
            field_values=build_aadhaar_field_values(
                name=application.field_values["applicantName"],
                date_of_birth=application.field_values["dob"],
                gender=application.field_values["gender"],
                aadhaar_number="0409322107754",
                address=application.field_values["address"],
            ),
        )

        # Act
        checks = self._checks_by_id(interactor.run_checks(request=request))

        # Assert
        assert (
            checks[f"{DOCUMENT_ID}:aadhaar-format"].status == CheckStatus.FAIL.value
        )
