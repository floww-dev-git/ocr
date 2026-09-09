# Reconciliation System — Complete Knowledge Base

## System Purpose

Automated fee distribution: when applicants pay fees via Razorpay, this system transfers the collected amounts to the correct government/third-party bank accounts via ICICI NEFT/RTGS. This is NOT payment collection — it's post-collection fund distribution.

## Three-Level Hierarchy (Verified from Models)

```
ReconciliationRequest (batch — business team CSV upload)
  │  Model: reconciliation_request.py
  │  PK: request_id
  │  Status: ReconciliationRequestStatus
  │  Contains: uploaded CSV, s3 keys, fee_head_amounts_csv, transactions_csv, failed_applications_csv
  │
  └── ApplicationReconciliation (per-app cycle — multiple cycles per app)
        │  Model: application_reconciliation.py
        │  PK: id (UUID)
        │  FK: request_id (nullable — can exist without batch request)
        │  Status: ApplicationReconciliationProcessStatus
        │  Contains: execution_arns (Step Function ARNs), result_json
        │
        └── ReconciliationTransaction (per-txn — actual NEFT bank transfer)
              │  Model: reconciliation.py
              │  PK: id (UUID)
              │  FK: application_reconciliation (nullable), sender_account, receiver_account
              │  Status: ReconciliationTransactionStatus
              │  Contains: bank_txn_id, utr_number, amount_in_rupees, notes, txn_type
              │
              └── TransactionContributedEntity (per-fee-header breakdown)
                    Model: reconciliation.py
                    FK: transaction
                    Contains: fee_header_id, amount_in_rupees, applied_config_type, fee_consolidation_category
```

## Status Machines (from enum.py)

### ReconciliationRequestStatus (batch lifecycle)
```
PREVIEW_GENERATION_IN_PROGRESS → PREVIEW_GENERATION_SUCCESS → APPROVED_FOR_INITIATION → QUEUED → IN_PROGRESS → COMPLETED
                              → PREVIEW_GENERATION_FAILED                                                     → PARTIALLY_FAILED
                                                                                                               → FAILED
                                                            → DISCARDED (admin cancels)
```

### ApplicationReconciliationProcessStatus (per-app cycle)
```
DRAFT → DRAFT_VERIFIED → PENDING → IN_PROGRESS → SUCCESS
                                               → FAILED
                                               → PARTIALLY_FAILED
                                               → PARTIALLY_RECONCILED (success but on-hold fee headers exist)
```
Execution allowed from: DRAFT_VERIFIED, PENDING, FAILED, PARTIALLY_FAILED

### ReconciliationTransactionStatus (per-txn — ICICI NEFT lifecycle)
```
DRAFT → DRAFT_VERIFIED → INITIATED → SUCCESSFULLY_DEBITED_FROM_SENDER_ACCOUNT
                                   → FAILED                   → POSTED_TO_RBI → SUCCESSFULLY_CREDITED_IN_RECEIVER_ACCOUNT
                                   → RETRY_STATUS_CHECK        → WAITING_FOR_BENE_BANK_CREDIT_CONFIRMATION → SUCCESSFULLY_CREDITED (or auto-credit after 72h)
                                                                                                           → REFUNDED (bank returned amount)
```

## End-to-End Reconciliation Flow

### Phase 1: Preview Generation (ReconciliationRequest)
1. Business team uploads CSV with application IDs via `GenerateReconciliationPreviewInteractor`
2. CSV stored in S3, request created with `PREVIEW_GENERATION_IN_PROGRESS`
3. Asynq event `GENERATE_RECONCILIATION_PREVIEW` emitted
4. For each application: ATR calculated, accounts mapped, draft transactions generated
5. Preview CSVs generated: fee_head_amounts, transactions, failed_applications
6. Status → `PREVIEW_GENERATION_SUCCESS` (or `FAILED`)
7. Admin reviews preview, approves → `APPROVED_FOR_INITIATION`

### Phase 2: ATR Calculation (CalculateAtrInteractor)
Per-application, calculates: **ATR = Consolidated Net Amount - Already Reconciled**

1. **Get fee consolidation** — calls `ApplicationFeeConsolidationInteractor.recalculate_application_fee_consolidation()` which rebuilds from scratch (delete + recreate)
2. **Get on-hold fee headers** — `ReconciliationOnHoldOce` split into resolved (custom config) and unresolved (excluded entirely)
3. **Get existing non-draft transactions** — amounts already transferred
4. **Calculate pending** — `consolidated[fee_header] - reconciled[fee_header]` per fee header
5. **Apply adjustments** — `ReconciliationAdjustmentAmount` cross-application offsets
6. Only positive amounts become transactions (negative = already over-reconciled)

### Phase 3: Account Mapping (ReconciliationAccountsMapper)
Maps each fee amount to sender/receiver bank accounts via `ReconciliationConfig`:

- **FEE_HEADER type** — direct `fee_header_id` → account mapping
  - `FIXED_ACCOUNT_ENUM`: static receiver account
  - `RULE_SET_ACCOUNT_ENUM`: dynamic via rules engine (engine_variables)
- **DIRECT_ORDER type** — for non-fee amounts (EXTRA_AMOUNT_PAID)
- **MISMATCH_AMOUNT type** — for rounding/unmatched amounts
- Supports **percentage splitting**: one fee header → multiple receivers (e.g., 70% govt, 30% agency)

### Phase 4: Transaction Building (ReconciliationTxnsBuilder)
- Groups amounts by `(sender_account, receiver_account)` pairs — optimizes into fewer transfers
- Transaction limit: 19 crore/txn — auto-splits above this
- Creates `ReconciliationTransaction` (DRAFT) + `TransactionContributedEntity` per fee header
- Atomically replaces existing drafts (`@transaction.atomic`)

### Phase 5: Step Function Execution (ReconciliationWorkflow v3.0)
**Triggered by:** `ReconciliationWorkflow().start_execution(input_data={"applicationReconciliationId": id})`
**Timeout:** 7 days
**Rate limit:** 5 apps processed, then 3-minute sleep

#### Step Function Operations:
1. **validate_and_categorize_transactions** — categorizes transactions into:
   - RetryStatus: already initiated, need status check only
   - Reinitiate: failed, need API retry
   - Initiate: new, need first-time ICICI API call
2. **ProcessAllTransactionTypesInParallel** — all 3 categories execute concurrently (3x faster)
3. **initiate_transactions** / **reinitiate_transactions** — ICICI NEFT API calls
4. **ProcessTransactions (Map, maxConcurrency=10)** — per-transaction debit/credit check loop:
   - CheckDebitStatus → poll every 30min, max 48 attempts (24h)
   - WaitForCreditCheck → initial 60min wait
   - CheckCreditStatus → poll every 120min, max 60 attempts (5 days)
   - 72h auto-credit: if status stuck at "Posted to RBI" or "Paid" for >72h → auto-mark credited
5. **DetermineTransactionStatus** — debit SUCCESS + credit SUCCESS = SUCCESS, else FAILED
6. **UpdateReconciliationStatus** — aggregates: all success = SUCCESS, all fail = FAILED, mixed = PARTIALLY_FAILED. If on-hold fee headers exist = PARTIALLY_RECONCILED

### Phase 6: Business Hours Enforcement
- **Operating hours:** 1:30 AM - 6:30 PM IST
- **Days:** Monday-Friday only
- **Bank holidays:** `BankHoliday` model checked
- `_is_weekday_business_hours()` guards Step Function initiation

## Key Models Deep Dive

### ReconciliationConfig (replaces deprecated FeeHeaderReconciliationConfig)
```
config_type: FEE_HEADER | DIRECT_ORDER | MISMATCH_AMOUNT
sender_account: FK(BankAccount) — source account
receiver_account: FK(BankAccount) — destination (nullable for rule_set)
account_type: FIXED_ACCOUNT_ENUM | RULE_SET_ACCOUNT_ENUM
fee_header_id: str — for FEE_HEADER type
rule_set_id: str — for dynamic account selection via engine_variables
```

### ReconciliationOnHoldOce
Fee headers temporarily excluded from reconciliation:
- `is_resolved=False` → completely excluded from ATR
- `is_resolved=True` + `recon_config_type` → uses custom config type for this fee header
- Unique on `(application_id, fee_header_id)`
- Used for: legal disputes, pending verification, special routing

### Naming Collision: Two `ApplicationReconciliationInteractor` Classes
Two classes share the same name — this is a known issue to be renamed:
- **Lifecycle manager** — `interactors/reconciliation/application_reconciliation_interactor.py` — manages Step Function initiation, business hours, status determination, pending app processing
- **ICICI executor** — `interactors/reconciliation/state_machine_handlers/application_reconciliation.py` — executes ICICI API calls, initiates/retries transactions, generates bank_txn_ids

When referencing in code or discussions, always use the FILE PATH to disambiguate. Renaming is planned.

### Canonical Status Enum: `ApplicationReconciliationProcessStatus`
Two enums exist but `ApplicationReconciliationProcessStatus` is canonical (matches model validator):
- `ApplicationReconciliationProcessStatus` — USE THIS: DRAFT, DRAFT_VERIFIED, PENDING, IN_PROGRESS, SUCCESS, FAILED, PARTIALLY_FAILED, PARTIALLY_RECONCILED
- `ApplicationReconciliationStatus` — AVOID: has extra values (DEBIT_CONFIRMED, CREDIT_PAID, REFUNDED, ERROR) used in some interactors but not the model validator

### Production Transaction Limit: 19 Crore
- Production NEFT limit: ₹19,00,00,000 (19 crore) per transaction — auto-split above this
- `txns_builder.py` `MAX_TRANSACTION_LIMIT_IN_RUPEES` may show a different value — trust 19 crore as the actual production limit
- Test transfer limit: ₹5 (`MAX_TRANSFER_AMOUNT_IN_RUPEES` in config.py) — only for `TransferBankAmountRequest`

### ReconciliationAdjustmentAmount (CRITICAL for upcoming features)
**What:** Cross-application amount corrections loaded via CSV by business team.

**Why it exists:** Business team sometimes misconfigures reconciliation or verifies incorrectly, causing money to be sent to wrong accounts for the wrong application. Instead of reversing the bank transfer (complex, slow), they adjust: the incorrectly-sent amount from app-A's transaction is offset against app-B's fee header during app-B's reconciliation.

**How it works:**
1. Business team uploads CSV with adjustment entries
2. Each entry links: `transaction` (from app-A) → `adjusted_application_id` (app-B) + `adjusted_fee_header_id` + `adjusted_amount`
3. During app-B's ATR calculation, `ApplyReconciliationAdjustmentsInteractor` subtracts `adjusted_amount` from the ATR for that fee header
4. Result: app-B reconciles less for that fee header because app-A already effectively covered it

**Validations on load:**
- `adjusted_amount` must be available in the target application for that fee header
- The referenced transaction must have reconciled at least `adjusted_amount`

**Unique constraint:** `(transaction, effected_fee_header_id, adjusted_application_id, adjusted_fee_header_id)`

**This is very crucial for upcoming features — agents must understand this flow thoroughly.** It's manual, error-prone, and affects financial correctness across applications.

### BankAccount
Master data — PK is `account_enum` (e.g., "TELANGANA_GOVT_ACCOUNT")
Contains: account_number, ifsc, beneficiary_id, account_name

### ReconciliationBankIntegration
ICICI API credentials: CIB reg API key, transaction API key, corp_id, user_id, aggr_name/id, URN, private_key, certificates

### IcIcIApiLog
Complete audit trail of every ICICI API call: encrypted request, decrypted response, timestamp, linked to transaction

### TransferBankAmountRequest
Separate feature for **test transfers** (not production reconciliation):
- Max 5 rupees per transfer
- Has own Step Function workflow
- Status: IN_PROGRESS → SUCCESS / FAILED / PARTIALLY_FAILED

## ICICI Bank API Integration

### APIs Used (from IcIcIApiEnum)
1. **CIB_REG_API** — registration/authentication
2. **COMPOSITE_TXN_API_V2** — initiate NEFT transfer
3. **CHECK_DEBIT_STATUS_API** — poll debit status
4. **CHECK_CREDIT_STATUS_API** — poll credit status (by UTR number)

### Transaction Types (ReconciliationTransactionType)
- **RGS** — regular NEFT (debit check → credit check → done)
- **TPA** — third-party account transfer (debit check alone = done, no credit check needed)

### Response Parsing
- Debit success: `STATUS=SUCCESS` AND `RESPONSE=SUCCESS` → INITIATED
- Credit status: `STATUS` field values:
  - `"Amount credited to Beneficiary."` → SUCCESSFULLY_CREDITED
  - `"Posted to RBI"` → POSTED_TO_RBI (72h auto-credit applies)
  - `"Paid"` → WAITING_FOR_BENE_BANK_CREDIT (72h auto-credit applies)
  - `"Amount refunded to Remitter."` → REFUNDED

### 72-Hour Auto-Credit Rule
If a transaction stays at "Posted to RBI" or "Paid" (WAITING) for >72 hours, it's auto-marked as SUCCESSFULLY_CREDITED. This follows RBI guidelines for NEFT settlement.

## Locks (from config.py)

| Operation | Lock Key | TTL |
|---|---|---|
| Application processing | `RECON_PROCESSING:{application_id}` | 120s |
| Request processing | `application_reconciliation_{application_id}` | 600s (in validate_and_categorize) |
| Draft generation | `GENERATE_RECONCILIATION_DRAFT-{pipeline_item_id}` | 120s |
| Adjustment load | `RECON_ADJUSTMENT_LOAD:{application_id}` | 120s |
| Transfer bank amount | `TRANSFER_BANK_AMOUNT:{request_id}` | 120s |

## Deprecated Models (still in code, don't use for new features)
- `FeeHeaderReconciliationConfig` — replaced by `ReconciliationConfig`
- `FixedOrderReconciliationConfig` — replaced by `ReconciliationConfig`
- `OrderReconciliationLog` — replaced by `TransactionContributedEntity`

## Amount Handling in Reconciliation
- **ReconciliationTransaction.amount_in_rupees** — `DecimalField(21,2)` — rupees, NOT paise
- **TransactionContributedEntity.amount_in_rupees** — `DecimalField(21,2)` — rupees
- **ATR calculation** uses `net_amount` from `ApplicationFeeConsolidation` — already in rupees
- **ICICI API** expects rupees as string
- No paise/rupees conversion needed within reconciliation — it's all rupees

## Critical Business Rules
1. An application can have MULTIPLE reconciliation cycles — reconcile ASAP as payments come in
2. TDR amounts are excluded (handled separately, no real money)
3. On-hold fee headers can be resolved with custom config types
4. Failed transactions are automatically retried on next Step Function execution
5. Business hours enforced (1:30 AM - 6:30 PM IST, Mon-Fri, no bank holidays)
6. Draft transactions are replaced atomically on each preview regeneration
7. Only DRAFT_VERIFIED transactions can be initiated (not DRAFT — must be verified first)
8. Production bank transfer limit: 19 crore (test transfers: 5 rupees)
9. 72h auto-credit on "Posted to RBI" / "Paid" stuck transactions
10. Step Function rate limit: process 5 apps, sleep 3 minutes, repeat
