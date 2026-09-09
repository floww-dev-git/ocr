# TDR Concurrency & Audit

TDR concurrency control uses Redis distributed locks plus Postgres row-level locking. Audit trail is maintained by `TransactionLog` for transactions and by `TDRManagementLog` for admin hold/release actions.

## Redis Locks

Four lock keys guard TDR writes. Constants and call-sites below are all verified against the repo — do not rename without updating every callsite.

| Lock | Name template | Defined in | Purpose |
|---|---|---|---|
| Account lock | `ACCOUNT_LOCK:{ACCOUNT_ID}` | `tdr/constants/config.py` as `TDR_ACCOUNT_LOCK` | Serialize writes to an account: balance updates, transaction creation on that account, sale accept/reject |
| Bank lock | `BANK_LOCK:{BANK_ID}` | `tdr/constants/config.py` as `TDR_BANK_LOCK` | Serialize account creation within a bank (account-number counter increment) |
| Creation ref lock | `CREATION_REF_LOCK:{CREATION_REF_ID}` | `tdr/constants/config.py` as `TDR_CREATION_REF_LOCK` | Prevent two parallel account-creation calls for the same source reference |
| Request lock | `TDR_REQUEST:{ENTITY_ID}` | `sales_crm_core/constants/config.py:2202` as `TDR_REQUEST_LOCK_NAME` | Serialize initiate / confirm / release on a single TDR request entity |

Default TTLs in `tdr/constants/config.py`: `AUTO_EXPIRY = 300` seconds, `TIMEOUT = 360` seconds.

**Why the request lock lives in sales_crm_core:** historical — the lock primitive and naming convention sit in `sales_crm_core`, so `tdr` imports it. When touching the request lock, import from `sales_crm_core.constants.config`, not from `tdr.constants.config`.

### Call sites

`TDR_ACCOUNT_LOCK`:
- `tdr/interactors/utilization/create_utilization_debit_transaction_to_account_bulk.py`
- `tdr/interactors/utilization/accept_tdr_transaction_by_owner.py`
- `tdr/interactors/utilization/release_build_now_transactions.py`
- `tdr/interactors/sale_and_transfer/initiate_tdr_sale_transaction.py`
- `tdr/interactors/sale_and_transfer/accept_tdr_sale_transaction.py`
- `tdr/interactors/sale_and_transfer/reject_tdr_sale_transaction.py`

`TDR_BANK_LOCK` + `TDR_CREATION_REF_LOCK`:
- `tdr/interactors/accounts/*` (account creation paths)

`TDR_REQUEST_LOCK_NAME`:
- `tdr/interactors/tdr_requests/utilization/initiate_tdr_requests.py` (line ~36)
- `tdr/interactors/tdr_requests/utilization/confirm_tdr_requests.py` (line ~31)
- `tdr/interactors/tdr_requests/utilization/release_tdr_requests.py` (line ~32)

Pattern in all three request call sites:
```python
lock_name = TDR_REQUEST_LOCK_NAME.format(ENTITY_ID=entity_id)
```

### Which lock to use — decision matrix

| Operation | Primary lock | Also needs |
|---|---|---|
| Create account (NEW_APPLICATION / SALE_AND_TRANSFER / DIGITALIZATION) | `TDR_BANK_LOCK` | `TDR_CREATION_REF_LOCK` |
| Debit transaction (UTILIZE, SALE) | `TDR_ACCOUNT_LOCK` | `@transaction.atomic` + `select_for_update()` on account row |
| Accept owner utilization via OTP | `TDR_ACCOUNT_LOCK` | — |
| Release build-now transaction | `TDR_ACCOUNT_LOCK` | — |
| Initiate / confirm / release TDR request | `TDR_REQUEST_LOCK_NAME` | `TDR_ACCOUNT_LOCK` when the inner transaction touches account balance |
| Hold / release account (admin) | `TDR_ACCOUNT_LOCK` | — |

**Combined locks:** when a TDR request confirms, it may need both the request lock (for state transition safety) and the account lock (for the underlying transaction). The outer interactor acquires request lock; inner transaction work acquires account lock. Always outermost → innermost, never the reverse.

## Postgres Locking Companion

`@transaction.atomic` + `select_for_update()` is used on every account row read-then-write. The Redis lock serializes distributed workers; the row lock protects against races within a single transaction that spans multiple reads. Both are needed; neither alone is sufficient.

Example pattern (see `sale_and_transfer/initiate_tdr_sale_transaction.py`):
```python
with acquire_lock(lock_name=TDR_ACCOUNT_LOCK.format(ACCOUNT_ID=account_id)):
    with transaction.atomic():
        account = Account.objects.select_for_update().get(id=account_id)
        # compute available balance, create SALE_INITIATED txn
```

## Transaction Audit (`TransactionLog`)

Every `Transaction` status change creates a `TransactionLog` row via `CreateTDRAccountTransactionLogInteractor`. The log is append-only — never updated, never deleted. Storage in `tdr/storages/` uses `bulk_create` for efficiency during digitalization.

The configio path has a parallel `TDRAccountTransactionLogConfig` for CSV round-tripping — see `tdr/interactors/configio/transaction_log/`.

`CreateTDRAccountTransactionWithoutLogsInteractor` exists as an **opt-out escape hatch** for bulk seeding where logs would be redundant (e.g., initial digitalization of historical data where logs are generated separately). Default is with logs.

## Admin Hold/Release Audit

`tdr/interactors/tdr_management/` runs a separate audit trail for admin-initiated account holds and releases. Every hold/release action:

1. Validates access via `ValidateTDRManagementAccess` (checks `TDR_MANAGEMENT` feature toggle and user identifications via IAM).
2. Acquires the account lock.
3. Updates status (`FUNCTIONAL` ↔ `ON_HOLD`) in Postgres and ES.
4. Creates a `TDRManagementLog` row via the hold/release interactor.

`GetTdrManagementLogsInteractor` returns the paginated audit. Never suppress the log write — it is the only trail for admin interventions.

See `tdr/interactors/tdr_management/CLAUDE.md` for details.

## Sanity Checks Are Lock-Free

`tdr/interactors/sanity_checks/` reads 3 data sources (Postgres, bps_service, sales_crm_service) and returns `List[FindingDTO]`. **No locks, no transactions, no writes.** Checks must remain pure — if a sanity check needs to acquire a lock or mutate state, it is being misused.

## Common Failure Modes

| Symptom | Likely cause |
|---|---|
| Available balance briefly wrong during sale | Missing `select_for_update()` inside the `ACCOUNT_LOCK` block |
| Duplicate accounts for the same BPS pipeline item | `TDR_CREATION_REF_LOCK` not acquired on the account-creation path |
| TDR request stuck in INITIATED | Lock acquired on wrong entity id (request lock is keyed by request entity id, not account id) |
| Audit row missing after transaction | Calling `CreateTDRAccountTransactionWithoutLogsInteractor` outside its intended digitalization bulk seed context |
| Admin hold succeeds but ES still shows FUNCTIONAL | ES update skipped — both Postgres and ES must update together inside the lock |
| Sanity check returning phantom findings | Context loader passed `Account.id` where `iam_account_id` is required for BPS service calls |

## Agent Checklist When Changing Concurrency

1. Adding a new write path? Identify which lock(s) from the table above apply. Never invent a new lock name — if a new lock is genuinely needed, discuss with dhruva and update this file.
2. Combining writes across accounts? Lock order must be deterministic (e.g., lower account_id first) to avoid deadlocks.
3. Reducing a TTL? That's a breaking change — confirm no long-running batch ops rely on the current value.
4. Moving a lock acquisition inside a loop? Stop. Either batch the operation outside the loop or lock once at the outer scope.
5. Sanity check needs a new source? Add it to `TDRAccountCheckContextLoader` — don't call storages inline from check functions.
