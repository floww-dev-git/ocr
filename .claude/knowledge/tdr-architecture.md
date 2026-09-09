# TDR Architecture

Architectural reference for the `tdr` app. For entity-by-entity detail see `tdr/CLAUDE.md` and `tdr/interactors/CLAUDE.md`. This file focuses on the *shape* of the system — the patterns and boundaries agents must respect.

## Bounded Context

`tdr` manages government-issued **development rights certificates** as tradable instruments. The unit of value is **square yards (`SQ_YARDS`)**, never money. TDR never participates in refund flows, ATR, or payment consolidation.

## Layer Map

```
tdr/
  models/tdr_bank.py                 # Bank, Account, Transaction, TransactionLog, TDRAccountRequest
  constants/                         # Enums (TransactionOperation, TransactionStatus, TDRRequestStatus, TDRBankType, CreationRefType), lock name templates
  dtos/                              # @dataclass DTOs — pure data, never ORM
  interactors/                       # One class per use case (see tdr/interactors/CLAUDE.md)
    accounts/                        # Register, hold, validate, balance calculation
    tdr_requests/                    # Request lifecycle + banks/ (strategy) + utilization/ + config/ + webhooks/
    utilization/                     # BuildNow transactions, OTP acceptance
    sale_and_transfer/               # Parent-child account linkage
    sanity_checks/                   # 55 pure-function invariant checks (no writes)
    tdr_management/                  # Admin hold/release with audit trail
    digitalization/                  # Registration of legacy certificates
    transactions/                    # Transaction CRUD + audit logs
    search/ + open_search/           # Elasticsearch/OpenSearch indexers
    configio/                        # BPS template import/export adapters
    letters/                         # PDF ledger generation
    mixins/                          # PaginationMixin, TDRBankMixin, TDRRequestMixin
  storage_interfaces/                # Abstract contracts (abc.ABC)
  storages/                          # Postgres + ES implementations
  adapters/service_adapter.py        # 12 lazy @property services
  app_interfaces/service_interface.py # Public API consumed by other apps via adapters
  exceptions/                        # 60+ domain exceptions inheriting BaseExceptionClass
```

Clean architecture rules (`.claude/rules/clean-architecture.md`, `interactors.md`, `storages.md`, `models.md`) apply verbatim. No Django imports in interactors. No model instances across layer boundaries. DTO-only.

## Core Domain Objects

| Entity | Role |
|---|---|
| `Bank` | Certificate issuing authority (GHMC, HMDA, etc). Different banks follow different workflows via `TDRBankType` |
| `Account` | Certificate holder's ledger. `initial_balance` is a `FloatField` **holding an area in SQ_YARDS**, not money |
| `Transaction` | Credit/debit entry against an account. Operations: `ISSUE`, `UTILIZE`, `SALE`, `DIGITALIZE` |
| `TransactionLog` | Append-only audit row for every status change on a `Transaction` |
| `TDRAccountRequest` | External purchase/utilisation request targeting an account |

`Account` is self-referential via `parent_account_id` — used by `RegisterSalesAndTransferTDRCertificateInteractor` to link child accounts created by a sale back to the seller's origin account.

## Strategy + Factory for Bank Behaviour

Different banks have wildly different workflows (external API, internal account, manual entry). The abstraction is `AbstractTDRBank` in `tdr/interactors/tdr_requests/banks/abstract_tdr_bank.py`:

Five abstract methods:
- `_initialize_capabilities() -> BankCapabilities`
- `validate_certificate(...) -> CertificateValidationResult`
- `initiate_tdr_requests_bulk(...) -> List[InitiateTDRRequestResponseDTO]`
- `release_tdr_requests(...) -> List[ReleaseTDRRequestResponseDTO]`
- `officer_accept_tdr_requests(...) -> List[ConfirmTDRRequestResponseDTO]`
- `update_tdr_requests(...) -> List[...]`

Four capability dataclasses on every implementation:
- `BankCapabilities` — top-level container with `bank_type`, plus the three below
- `ValidationCapabilities` — `supports_api_validation`, `requires_holder_otp`, `skip_area_validation`
- `OperationSupport` — `can_initiate`, `can_release`, `can_officer_accept`
- `StatusTransitions` — `after_validation`, `after_initiation` (Optional), `after_confirmation`

Agents choosing where behaviour belongs: if it varies per bank, it goes on the bank class. If it is uniform across banks, it goes in the calling interactor.

**Dispatch rule:** always via `TDRBankFactory.get_bank(bank_type)`. Never inline `if bank_type == "TELANGANA"`. See `.claude/knowledge/tdr-banks.md` for the three implementations.

## Service Adapter

`tdr/adapters/service_adapter.py` holds 12 lazy `@property` services (NB: `tdr/CLAUDE.md` currently says "11 adapters" — stale, ignore):
`sales_crm_service`, `iam_service`, `field_service`, `record_service`, `user_service`, `automation_workflow`, `payments_engine`, `bps_service`, `rules_engine`, `asynq_service`, `plugins`, `graphql_service`.

All external service access goes through `get_service_adapter().<service>`. Never import from another app's internals.

## Public API (`app_interfaces/service_interface.py`)

Consumed exclusively via adapter. `TDRAdapter` in `bps/adapters/tdr_adapter.py` is a thin pass-through of `TDRServiceInterface` methods (~35 methods covering accounts, transactions, sale & transfer, digitalization, configio, and request cost roll-ups). See `.claude/knowledge/tdr-bps-integration.md` for how BPS uses this.

## DTO Discipline

Per global rule (user memory): **DTOs between interactors and storages; never optional attributes unless the field is genuinely sometimes-absent**. Every storage interface method takes/returns a DTO. Every interactor receives DTOs via its public method and returns DTOs. No Django models cross this line. `.value` is used at runtime for enums; typing uses the enum class with `# noinspection PyTypeChecker`.

## Creation Reference (Important for configio/sanity_checks)

`Account.creation_ref_type` identifies *how* an account was created:
- `NEW_APPLICATION` — via BPS pipeline (standard case)
- `DIGITALIZATION` — legacy record loaded through `digitalization/`
- `SALE_AND_TRANSFER` — child account from a sale

This matters because the approval/rejection stage IDs and the required certificate set differ per creation ref. Config selection must branch on `creation_ref_type`, never default silently. See `tdr/interactors/sanity_checks/CLAUDE.md` and `REQUIRED_CERTIFICATES_MAP`, `APPROVED_STAGE_IDS_MAP`, `REJECTED_STAGE_IDS_MAP` under `tdr/interactors/sanity_checks/constants/`.

## Indexing

Two search backends: Elasticsearch (`tdr/interactors/search/`) for the CRM-facing list and OpenSearch (`tdr/interactors/open_search/`) for external discovery. Every account write goes through `ReindexTDRAccountsInteractor` or the balance/status update variants. Storage interface: `TDRElasticsearchStorageInterface`.

## What Lives Where — Quick Map

| Question | Source |
|---|---|
| "How does the utilization request flow move through statuses?" | `.claude/knowledge/tdr-flows.md` |
| "Which bank supports which operations?" | `.claude/knowledge/tdr-banks.md` |
| "How does BPS create a TDR account?" | `.claude/knowledge/tdr-bps-integration.md` |
| "What locks protect a sale transaction?" | `.claude/knowledge/tdr-concurrency-and-audit.md` |
| "What's in the Account model?" | `tdr/models/tdr_bank.py` |
| "What interactor creates a transaction?" | `tdr/interactors/transactions/` |
| "What sanity checks run on an account?" | `tdr/interactors/sanity_checks/CLAUDE.md` |
