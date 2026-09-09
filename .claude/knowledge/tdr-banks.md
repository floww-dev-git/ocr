# TDR Banks — Strategy Implementations

Three concrete implementations of `AbstractTDRBank`. All dispatch goes through `TDRBankFactory.get_bank(bank_type)` at `tdr/interactors/tdr_requests/banks/tdr_bank_factory.py`.

For the abstract contract (capability dataclasses, method signatures) see `tdr/interactors/tdr_requests/banks/abstract_tdr_bank.py` and `.claude/knowledge/tdr-architecture.md`.

## Capability Matrix

| Capability | TELANGANA | BUILD_NOW | MANUAL |
|---|---|---|---|
| `supports_api_validation` | True | True | False |
| `requires_holder_otp` | **True (only one)** | False | False |
| `skip_area_validation` | False | False | True |
| `can_initiate` | True | True | False |
| `can_release` | True | True | False |
| `can_officer_accept` | True | True | True |
| `after_validation` | CERTIFICATE_VALIDATED | CERTIFICATE_VALIDATED | DRAFT |
| `after_initiation` | INITIATED | INITIATED | None |
| `after_confirmation` | CONFIRMED | CONFIRMED | ACCEPTED |

Values taken directly from each implementation's `_initialize_capabilities()`. Do not re-assert capability values from memory — re-read the source when in doubt.

## TELANGANA

**File:** `tdr/interactors/tdr_requests/banks/implementations/telangana/telangana_tdr_bank.py` (437 lines).

External Telangana state government API integration. Uses `TelanganaAdapter` (in the same folder) as REST client. Endpoints exercised: `ValidateTDR`, `InitiateTDRRequest`, `ReleaseTDR`, `ConfirmTDR`. The adapter has mock responses for `alpha`/`local` stages.

Distinguishing behavior:
- **Only bank requiring holder OTP**. After `validate_certificate` returns `needs_holder_verification=True`, the flow moves to `CERTIFICATE_OWNERSHIP_VERIFIED` only after OTP verification (see `VerifyTDRRequestOTPInPortalInteractor`).
- Has a `TDRRequestAuthority`-based config map — different Telangana authorities may route to different endpoints.
- Holder name resolution via `iam_service` with a defensive try/except fallback (`_resolve_user_name`).
- Area validation against the certificate's allocated area.

**When to route here:** eligible bank types are determined by `GetEligibleTDRBanksInPortalInteractor` via rules engine. `DetermineTDRBankTypeInteractor` picks the actual bank based on whether a certificate already exists.

## BUILD_NOW

**File:** `tdr/interactors/tdr_requests/banks/implementations/build_now/build_now_tdr_bank.py` (269 lines).

Internal "Build Now" construction program. No external API — validation is against TDR accounts already held in our own system.

Distinguishing behavior:
- Validation is **account-based**: `validate_certificate_with_build_now` checks a certificate number against existing `Account` records in our DB, not an external system.
- Uses `BuildNowResponseBuilder` to convert raw transaction outcomes into `InitiateTDRRequestResponseDTO` / `ConfirmTDRRequestResponseDTO`.
- Uses `BuildNowTransactionManager` to orchestrate transaction lifecycle (initiate → confirm → accept → release).
- No holder OTP — trusted internal flow.
- Lazy imports record_service and sales_crm_service via `get_service_adapter()`.

**Key distinction from the app-level `utilization/` folder:** BuildNow debit transactions (`CreateUtilizationDebitTransactionToAccountBulkInteractor`, `AcceptTDRTransactionByOwnerInteractor`, etc.) live in `tdr/interactors/utilization/` — those are the per-account transaction primitives. The BuildNow *bank* orchestrates TDR *requests* that internally call those primitives.

## MANUAL

**File:** `tdr/interactors/tdr_requests/banks/implementations/manual/manual_tdr_bank.py` (238 lines).

Manual entry / operations-officer verified. No API, no programmatic validation.

Distinguishing behavior:
- `validate_certificate()` returns a stub: `is_valid=True`, `allocated_area=0.0`, `market_value=0.0`, `info="Certificate requires manual verification by operations officer"`, `skip_area_validation=True`.
- `initiate_tdr_requests_bulk()` returns `[]` (no-op — cannot initiate).
- `update_tdr_requests()` returns `[]`.
- State machine short-circuits: `DRAFT → (no INITIATED) → ACCEPTED` on officer acceptance.
- Agents reviewing a MANUAL flow should not expect an INITIATED or CONFIRMED status on the request.

**When MANUAL is chosen:** the rules engine decides based on pipeline configuration. MANUAL exists so operators can record off-system certificates without blocking on API integration.

## Common Agent Mistakes

1. **Hardcoding bank checks.** `if bank_type == TDRBankType.TELANGANA.value` inside an interactor is a red flag — the correct pattern is `self.bank_factory.get_bank(bank_type).<method>()`. Add bank-specific logic to the bank class, not the caller.

2. **Assuming `requires_holder_otp` across banks.** Only TELANGANA requires OTP. A MANUAL or BUILD_NOW flow that routes through OTP paths is a bug.

3. **Assuming MANUAL has an INITIATED state.** It doesn't. Validate stage transition logic against the bank's `StatusTransitions` before asserting a request progresses through INITIATED.

4. **Forgetting `skip_area_validation`.** MANUAL skips area validation because allocated area is unknown at intake. TELANGANA and BUILD_NOW enforce it.

5. **Wrong certificate source for BUILD_NOW.** BUILD_NOW validation is against *our own* `Account` records — not an external API. If you see HTTP calls in a BuildNow validation path, something is off.

## Adding a New Bank

1. Add an entry to `TDRBankType` enum (`tdr/constants/enums.py`).
2. Create a new implementation folder under `tdr/interactors/tdr_requests/banks/implementations/<bank>/`.
3. Subclass `AbstractTDRBank`, implement `_initialize_capabilities()` and all abstract methods.
4. Register the new class inside `TDRBankFactory.get_bank()`.
5. If the bank needs rules-engine eligibility, update `GetEligibleTDRBanksInPortalInteractor` inputs.
6. If it introduces a new status transition, update `.claude/knowledge/tdr-flows.md` and confirm the rules in `constants/enums.py` permit it.
