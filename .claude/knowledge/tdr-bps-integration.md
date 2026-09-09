# TDR ↔ BPS Integration

The `bps` and `tdr` apps cross-talk more than any other pair. This file explains *how* — and clears up a naming clash that bites every agent at least once.

## Critical Disambiguation: Two Different "TDR Requests"

The word "TDR request" means two different things in two different apps. Never conflate them.

| Name | App | What It Is | State Machine |
|---|---|---|---|
| **`TdrRequest`** (singular, capital R) | `bps` | "Technical Document Review" — a secondary review workflow within a BPS application, one of BPS's four-domain parallel structure (Application / TdrRequest / SiteInspection / Verification) | `NOT_STARTED → IN_PROGRESS → SUBMITTED → APPROVED / REJECTED → RESUBMITTED ...` (shared across all four BPS domains) |
| **`TDRRequest`** (the module `tdr_requests/`) | `tdr` | The utilization-request lifecycle for an actual TDR certificate (a credit on a TDR `Account`) | `DRAFT → CERTIFICATE_VALIDATED → (CERTIFICATE_OWNERSHIP_VERIFIED) → INITIATED → CONFIRMED → ACCEPTED` |

These are **entirely separate entities** with separate state machines, separate storages, and separate purposes. `bps.TdrRequest` is about reviewing documents attached to an application. `tdr/interactors/tdr_requests/` is about spending certificate area.

When the user or another agent says "TDR request", default to the `tdr` app meaning unless context is clearly BPS document review.

## The Adapter Boundary

All BPS-to-TDR traffic flows through the adapter:

```
bps/<caller>.py
  ↓ (via get_service_adapter().tdr_service)
bps/adapters/tdr_adapter.py     # TDRAdapter — pass-through
  ↓ (instantiates the public interface)
tdr/app_interfaces/service_interface.py   # TDRServiceInterface
  ↓ (delegates to interactors + storages)
tdr domain logic
```

`TDRAdapter` is a **thin pass-through**: every method forwards to `TDRServiceInterface`. It does not add logic. Agents adding new cross-app methods follow this pattern — extend `TDRServiceInterface` (with @staticmethod wrapping an interactor call), then surface it on `TDRAdapter`.

**Rule:** BPS code never imports TDR internals (`tdr.interactors.*`, `tdr.storages.*`, `tdr.models.*`). Only `bps.adapters.tdr_adapter` touches `tdr.app_interfaces`. Enforced by the project-wide app isolation rule (`.claude/rules/clean-architecture.md`).

## Primary Integration Points

### a. Account creation from BPS pipeline

Entry: `bps/interactors/tdr/*` orchestrates pipeline-item data capture, then calls `TDRAdapter.register_tdr_certificate(params_dto, initiated_by)` → `RegisterTDRCertificateInteractor`.

Linkage: `Account.creation_ref_id = pipeline_item_id`, `Account.creation_ref_type = NEW_APPLICATION.value`.

After creation, the account number is written *back* into a pipeline item field (via `field_service`) so the BPS UI can display it. The write-back is part of the BPS side, not TDR.

### b. BPS configio handlers

`bps/configio/tdr/` contains the CSV import/export handlers for TDR (accounts, transactions, transaction logs, utilization notifications, sales & transfer notifications). These follow the configio architecture in `.claude/rules/configio-architecture.md`:
- `bps/configio/tdr/run_actions_handlers/` — action handlers, must call through `get_service_adapter().tdr_service.<method>` — never import TDR internals directly.
- `tdr/interactors/configio/` — the domain-side implementations the adapter eventually hits.

Methods on `TDRAdapter` serving this path: `get_tdr_accounts`, `get_accounts_json`, `convert_account_json_to_dto`, `run_checks_for_create_tdr_account`, `create_tdr_account`, plus parallel sets for transactions, transaction logs, utilization notifications, and sales-and-transfer notifications.

### c. Certificate regeneration

When BPS updates a field response that affects certificate content, TDR publishes `EventType.REGENERATE_TDR_CERTIFICATE_LETTER` (`common/constants/enums.py:698`) with group-id `"{pipeline_item_id}"`. An async handler in `plugins` regenerates the PDF. Details in `.claude/knowledge/tdr-flows.md` §4.

### d. Utilization request cost roll-up

`TDRAdapter.get_total_cost_of_tdr_requested_area(pipeline_item_id, pipeline_item_type)` returns `SUM(market_value × requested_area)` across all TDR requests on the pipeline item. BPS / fee_engine use this when pricing a pipeline item — TDR itself is not priced, but its *utilization via BuildNow* can have an associated monetary cost.

### e. Sanity checks — BPS-side data access

`tdr/interactors/sanity_checks/` loads context from three sources: the TDR Postgres storage, `bps_service` (pipeline items, field responses, stage configs), and `sales_crm_service` (user and pipeline data). **Critical rule:** BPS service calls take `iam_account_id` — not the TDR `Account.id`. Passing the wrong identifier returns empty/wrong data silently. This has been the #1 recurring bug in the sanity-check work (see tdr-agent memory).

### f. Pipeline item type dispatch

TDR requests can target two entity types (`TDREntityType.PIPELINE_ITEM` and `TDREntityType.PAYMENT`). `GetPipelineItemForTDRRequestInteractor` resolves the pipeline item ID from either. PDF generation in `tdr/interactors/tdr_requests/letters/` handles both paths.

## Events BPS Observes

| Event | Publisher | Subscriber behavior |
|---|---|---|
| `ALL_TDR_REQUESTS_ACCEPTED` | `tdr/interactors/tdr_requests/utilization/accept_tdr_request.py` | `automation_workflows` advances the pipeline stage via the rules engine |
| `REGENERATE_TDR_CERTIFICATE_LETTER` | `tdr` (on account-field change) | `plugins` regenerates the PDF |
| `PIPELINE_ITEM_ORDERS_PROCESSING_STARTED` | BPS side | May trigger TDR account creation preparation |

## Agent Checklist When Touching This Boundary

1. Does your change require a new method on `TDRServiceInterface`? If yes, add it to `TDRAdapter` in the same PR (pass-through).
2. Did you import from `tdr.interactors`, `tdr.storages`, or `tdr.models` from BPS? That is a cross-app violation — go through the adapter.
3. If the change affects field IDs used by TDR (`certificate_*`, stage IDs, required docs), update `tdr/interactors/sanity_checks/constants/` — stale maps cause silent check skips.
4. If the change adds a new `creation_ref_type` value, update `REQUIRED_CERTIFICATES_MAP`, `APPROVED_STAGE_IDS_MAP`, `REJECTED_STAGE_IDS_MAP`.
5. If your BPS code reads from TDR, always pass `iam_account_id` on the TDR side — never `Account.id`.
6. For configio changes, verify `run_actions_handlers` in `bps/configio/tdr/` are calling through the service adapter, not instantiating TDR handlers directly.

## What This Integration Is NOT

- TDR is **not** part of the fee/payment domain. It has no monetary amounts on accounts or transactions. TDR penalties (the only monetary slice) are charged via the payments domain, not TDR.
- TDR is **excluded** from refund chains, normal ATR reconciliation, and consolidation `base_amount` — see `.claude/knowledge/fees-payments.md` and `.claude/knowledge/fee-consolidation.md` for the exclusion rules.
- `bps.TdrRequest` (document review) has **zero** coupling to TDR certificates. Do not route one flow through the other.
