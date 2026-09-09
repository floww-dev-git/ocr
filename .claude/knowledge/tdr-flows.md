# TDR Business Flows

Four end-to-end flows every agent working on TDR should understand. Entity and file detail live in `tdr/interactors/CLAUDE.md` and `tdr/interactors/tdr_requests/CLAUDE.md` — this file focuses on *what happens in what order and why*.

## 1. TDR Request Utilization Lifecycle

This is the happy path for utilizing an existing certificate against a pipeline item (e.g., to unlock FSI in a Build Now application).

```
DRAFT
  └─ CreateTDRRequestInPortalInteractor           (request row in DRAFT)
CERTIFICATE_VALIDATED
  └─ ValidateTDRRequestCertificateNumberInteractor
       → TDRBankFactory.get_bank(bank_type).validate_certificate(...)
CERTIFICATE_OWNERSHIP_VERIFIED   (TELANGANA only — OTP path)
  └─ VerifyTDRRequestOTPInPortalInteractor
INITIATED
  └─ InitiateTDRRequestApiInteractor
       → bank.initiate_tdr_requests_bulk(...)
       → acquires TDR_REQUEST_LOCK per entity_id
CONFIRMED
  └─ ConfirmTDRRequestsInteractor
       → bank.officer_accept_tdr_requests(...)
ACCEPTED
  └─ AcceptTDRRequestInteractor
       → when ALL requests on the pipeline item reach ACCEPTED →
         publishes ALL_TDR_REQUESTS_ACCEPTED event →
         automation_workflows advances the pipeline stage
```

**Bank-specific shortcuts:**
- MANUAL: `DRAFT → ACCEPTED` directly on officer acceptance (no INITIATED, no CONFIRMED, no OTP).
- BUILD_NOW: skips `CERTIFICATE_OWNERSHIP_VERIFIED` (no OTP).
- TELANGANA: full 6-state path including OTP.

**Release path:** any non-terminal state can be released via `ReleaseTDRRequestsInteractor` → `bank.release_tdr_requests(...)`. Release is the cancel equivalent — it unwinds in-progress debit effects on the source account's available balance.

**Invariant:** a pipeline item can have multiple TDR requests; stage auto-advance fires only when every request on that item is ACCEPTED.

## 2. Sales & Transfer

Transfers part (or all) of an `Account`'s available balance to a new holder, creating a child account.

```
Initiate
  └─ InitiateTDRSaleTransactionInteractor
       → validates area availability (ValidateTDRAccountAreaAvailabilityForSaleInteractor)
       → creates SALE_INITIATED transaction on seller account
       → acquires ACCOUNT_LOCK on seller account
Accept
  └─ AcceptTDRSaleTransactionInteractor
       → RegisterSalesAndTransferTDRCertificateInteractor creates child Account
         with parent_account_id = seller.id, creation_ref_type = SALE_AND_TRANSFER
       → SALE_RELEASED on seller, SALE_COMPLETED on child
Reject
  └─ RejectTDRSaleTransactionInteractor
       → SALE_RELEASED on seller (no child account created)
```

Transaction status sequence: `SALE_INITIATED → SALE_RELEASED → SALE_COMPLETED`.

**Available balance impact:** while `SALE_INITIATED` is open, the area is subtracted from seller's available balance (counts as "in progress"). On rejection, it flows back. On acceptance, it's permanently debited and credited to the child account as `initial_balance`.

## 3. Application / Account Creation Types

Three entry points, differing by `Account.creation_ref_type`:

| Type | Entry Interactor | Creation Source |
|---|---|---|
| `NEW_APPLICATION` | `RegisterTDRCertificateInteractor` | BPS pipeline item (normal path via `TDRAdapter`) |
| `DIGITALIZATION` | `RegisterDigitalTDRCertificateInteractor` | Bulk legacy data load — creates account + all historical transactions in one atomic call |
| `SALE_AND_TRANSFER` | `RegisterSalesAndTransferTDRCertificateInteractor` | Child account spawned by accepted sale (see flow 2) |

**Why this matters for config selection:** approved/rejected stage IDs and required certificate document sets differ per creation ref type. The maps `APPROVED_STAGE_IDS_MAP`, `REJECTED_STAGE_IDS_MAP`, `REQUIRED_CERTIFICATES_MAP` in `tdr/interactors/sanity_checks/constants/` are keyed by `creation_ref_type`. Silently defaulting to `NEW_APPLICATION` config for a `DIGITALIZATION` or `SALE_AND_TRANSFER` account is a repeated source of bugs — always branch on `creation_ref_type`.

**Concurrency:** account creation acquires `BANK_LOCK:{BANK_ID}` to serialize account-number allocation, and `CREATION_REF_LOCK:{CREATION_REF_ID}` to prevent duplicate accounts for the same source reference.

## 4. Certificate Regeneration (BPS ↔ TDR ↔ Plugins)

When an account's certificate-relevant fields change (e.g., a field response is updated in BPS), the PDF certificate letter must be regenerated.

```
BPS interactor updates account data (via TDRAdapter)
  → TDR publishes EventType.REGENERATE_TDR_CERTIFICATE_LETTER
    (event group id pattern: "{pipeline_item_id}")
  → asynq event handler subscribes
  → plugins service regenerates the PDF letter
  → updated letter written back to the pipeline item's document store
```

Event locations:
- `common/constants/enums.py:698` — `EventType.REGENERATE_TDR_CERTIFICATE_LETTER`
- `common/constants/enums.py:762` — `EventTypeGroupIdPattern.REGENERATE_TDR_CERTIFICATE_LETTER`

This is a *cross-app side effect* — the TDR domain does not render PDFs, and the `plugins` app does not own account state. The event bus is the handoff.

**Companion event:** `TDRRequestTriggerEventType.ALL_TDR_REQUESTS_ACCEPTED` (`automation_workflows/constants/enum.py:1174`) is fired by `AcceptTDRRequestInteractor` when every request on a pipeline item is accepted, and triggers a stage transition in `automation_workflows`.

## Balance Calculation Rule (applies to all flows)

```
available_balance = initial_balance
                  - SUM(area of in_progress UTILIZE txns)
                  - SUM(area of in_progress SALE txns)

in_progress statuses: UTILIZATION_INITIATED, UTILIZATION_ACCEPTED_BY_OFFICER, SALE_INITIATED
```

Implemented by `CalculateTDRAccountAvailableBalanceInteractor` (and bulk variants). Any new transaction status that represents a "reserved but not settled" state must be added to the in-progress set, or the balance math silently leaks area.

## Sanity Checks Overlay

`tdr/interactors/sanity_checks/` runs 55 pure checks across 7 categories on top of these flows. They never mutate — they emit `FindingDTO` lists. The loader reads from Postgres, bps_service, and sales_crm_service; BPS calls there take `iam_account_id` (not TDR `Account.id`). See `tdr/interactors/sanity_checks/CLAUDE.md`.
