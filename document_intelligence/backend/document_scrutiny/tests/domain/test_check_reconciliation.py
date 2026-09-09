from document_scrutiny.constants.enums import CheckGroup, CheckStatus
from document_scrutiny.domain.check_reconciliation import CheckReconciliation
from document_scrutiny.dtos.check_dtos import CheckDTO

DOCUMENT_ID = "document_1"


def build_check(
    key: str,
    status: str = CheckStatus.PASS.value,
    group: str = CheckGroup.RULE.value,
    title: str = "A check",
    acknowledged: bool = False,
    manual: bool = False,
    requested: bool = False,
) -> CheckDTO:
    return CheckDTO(
        check_id=f"{DOCUMENT_ID}:{key}",
        document_id=DOCUMENT_ID,
        group=group,
        title=title,
        status=status,
        detail="detail",
        acknowledged=acknowledged,
        manual=manual,
        requested=requested,
    )


class TestCheckReconciliation:
    def test_recomputed_status_replaces_the_previous_one(self):
        previous = (build_check("name", status=CheckStatus.WARN.value),)
        recomputed = (build_check("name", status=CheckStatus.PASS.value),)

        merged, changed_ids = CheckReconciliation.merge(
            previous_checks=previous, recomputed_checks=recomputed
        )

        assert merged[0].status == CheckStatus.PASS.value
        assert changed_ids == (f"{DOCUMENT_ID}:name",)

    def test_a_status_that_did_not_move_is_not_reported_as_changed(self):
        previous = (build_check("name", status=CheckStatus.PASS.value),)
        recomputed = (build_check("name", status=CheckStatus.PASS.value),)

        merged, changed_ids = CheckReconciliation.merge(
            previous_checks=previous, recomputed_checks=recomputed
        )

        assert merged[0].status == CheckStatus.PASS.value
        assert changed_ids == ()

    def test_officer_resolutions_survive_a_recheck(self):
        previous = (
            build_check(
                "dob",
                status=CheckStatus.WARN.value,
                acknowledged=True,
                requested=True,
            ),
        )
        recomputed = (build_check("dob", status=CheckStatus.WARN.value),)

        merged, _ = CheckReconciliation.merge(
            previous_checks=previous, recomputed_checks=recomputed
        )

        assert merged[0].acknowledged is True
        assert merged[0].requested is True

    def test_a_newly_appearing_check_is_reported_as_changed(self):
        merged, changed_ids = CheckReconciliation.merge(
            previous_checks=(),
            recomputed_checks=(build_check("pan-format"),),
        )

        assert len(merged) == 1
        assert changed_ids == (f"{DOCUMENT_ID}:pan-format",)

    def test_the_issuer_answer_is_kept_even_though_it_cannot_be_recomputed(self):
        issuer = build_check(
            "issuer",
            status=CheckStatus.WARN.value,
            group=CheckGroup.EXTERNAL.value,
            title="Income Tax Department did not fully match",
        )
        previous = (build_check("name", status=CheckStatus.WARN.value), issuer)
        recomputed = (build_check("name", status=CheckStatus.PASS.value),)

        merged, changed_ids = CheckReconciliation.merge(
            previous_checks=previous, recomputed_checks=recomputed
        )

        assert merged[-1] == issuer
        assert changed_ids == (f"{DOCUMENT_ID}:name",)

    def test_recomputed_checks_keep_their_given_order_ahead_of_the_issuer_answer(self):
        previous = (
            build_check("issuer", group=CheckGroup.EXTERNAL.value),
            build_check("name"),
        )
        recomputed = (build_check("name"), build_check("dob"), build_check("pan"))

        merged, _ = CheckReconciliation.merge(
            previous_checks=previous, recomputed_checks=recomputed
        )

        assert [check.check_id.split(":")[-1] for check in merged] == [
            "name",
            "dob",
            "pan",
            "issuer",
        ]
