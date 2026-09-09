import dataclasses

from document_scrutiny.constants.enums import CheckStatus
from document_scrutiny.domain.cleared_field_check import ClearedFieldCheck
from document_scrutiny.interactors.run_document_checks_interactor import (
    RunDocumentChecksInteractor,
)
from document_scrutiny.tests.conftest import (
    DOCUMENT_ID,
    MISMATCH_APPLICATION_ID,
    build_pan_checks_request,
    build_pan_field_values,
)

MISREAD_NAME = "MOHAMMED IRFAN SIDDIQI"
WRONG_PAN = "ZZZZZ9999Z"


def build_values(**overrides) -> tuple:
    values = build_pan_field_values(
        name=MISREAD_NAME,
        parent_name="MOHAMMED YOUSUF SIDDIQUI",
        date_of_birth="1982-11-27",
        pan="BNMPS7720K",
    )
    if not overrides:
        return values
    return tuple(
        dataclasses.replace(value, **overrides[value.key])
        if value.key in overrides
        else value
        for value in values
    )


def run_checks(field_values) -> list:
    return RunDocumentChecksInteractor().run_checks(
        request=build_pan_checks_request(
            application_id=MISMATCH_APPLICATION_ID, field_values=field_values
        )
    )


class TestOfficerClearedField:
    def test_a_field_the_officer_cleared_still_raises_a_check(self):
        # Arrange
        values = build_values(pan={"value": "", "edited": True})

        # Act
        checks = run_checks(values)

        # Assert
        pan_check = next(
            check for check in checks if check.check_id == f"{DOCUMENT_ID}:pan"
        )
        assert pan_check.status == CheckStatus.WARN.value
        assert "cleared by the officer" in pan_check.title

    def test_clearing_a_field_cannot_delete_a_failing_check(self):
        # Arrange
        failing = run_checks(build_values(pan={"value": WRONG_PAN}))
        assert any(check.status == CheckStatus.FAIL.value for check in failing)

        # Act
        after_clearing = run_checks(
            build_values(pan={"value": "", "edited": True})
        )

        # Assert
        assert f"{DOCUMENT_ID}:pan" in {check.check_id for check in after_clearing}

    def test_a_field_nobody_ever_read_still_raises_no_check(self):
        # Arrange
        values = build_values(pan={"value": ""})

        # Act
        checks = run_checks(values)

        # Assert
        assert f"{DOCUMENT_ID}:pan" not in {check.check_id for check in checks}

    def test_a_cleared_field_keeps_the_place_of_the_check_it_replaces(self):
        # Act
        checks = run_checks(build_values(name={"value": "", "edited": True}))

        # Assert
        assert checks[0].check_id == f"{DOCUMENT_ID}:name"

    def test_the_check_points_at_the_field_the_officer_must_revisit(self):
        # Act
        check = ClearedFieldCheck.build(
            document_id=DOCUMENT_ID,
            field_spec=next(
                spec
                for spec in build_pan_checks_request().document_type.field_specs
                if spec.key == "name"
            ),
        )

        # Assert
        assert check.field_key == "name"
        assert check.status == CheckStatus.WARN.value

    def test_clearing_the_pan_also_withdraws_its_format_verdict(self):
        # A format opinion on an empty string would be noise, not evidence.
        # Act
        checks = run_checks(build_values(pan={"value": "", "edited": True}))

        # Assert
        assert f"{DOCUMENT_ID}:pan-format" not in {
            check.check_id for check in checks
        }
