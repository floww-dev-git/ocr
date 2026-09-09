# Fees & Payments Knowledge Base

## Architectural Decisions

| Decision | Choice | Why | Trade-off |
|---|---|---|---|
| Amount storage unit | Paise (int) for orders/OCEs | Avoids floating point rounding | Requires boundary conversion to rupees |
| OCE payment atomicity | Full OCE or nothing | Simplifies reconciliation math | Can't split a single OCE across payments |
| Selective OCE payment | Applicant picks which OCEs to pay | Real-world need — pay selected fee heads now, rest later | Order becomes PARTIALLY_PAID (derived status) |
| Three OCE amount fields | `amount`, `effective_amount`, `revised_amount` — each for different contexts | Setoff, recalculation, and original are independent concerns | Must know which field to use where |
| Direct orders vs fee engine | `allow_partial=False` = no OCE selection | Processing fees are fixed, non-splittable | Two order types with different payment rules |
| INITIATED timeout (5min) | Auto-revert to YET_TO_PAY | Handle abandoned payment attempts | Must re-initiate after timeout |
| Fee recalc at payment time | Check before Razorpay order creation | Fees can change between order creation and payment | Adds latency, but prevents charging wrong amount |
| Webhook idempotency | Redis lock (600s) + DB unique constraint | Prevents double-processing | Lock TTL limits throughput on same order |
| Refund validation | Triple chain (app -> order -> fee config) | Defense in depth | Three DB lookups per refund initiation |
| Reconciliation ATR | Delete + recreate consolidation | Guarantees fresh snapshot | Higher write volume, but correctness > performance |
| Status transitions | Whitelist allowed, reject all others | Prevents impossible states | Every new state requires config update |
| TDR as non-monetary | Certificates, not Razorpay money | Government requirement (GHMC/HMDA) | Must exclude from refunds, recon, consolidation |
| Razorpay captured -> PAID | Internal `PAID` = Razorpay `captured` | Simplifies internal status machine | Must remember mapping when reading Razorpay docs |
| PARTIALLY_PAID derived | Computed from OCE payments vs order amount | Always reflects current truth | Not a stored transition — recomputed on read |
| Three-level reconciliation | Request -> AppRecon -> Transaction | Business team controls batch, system handles per-app cycles | More complex but allows partial retries |

## Known Compromises

| Compromise | Reason | Impact | Resolution Path |
|---|---|---|---|
| Webhook signature validation DISABLED | Was causing false rejections during dev | P0 security gap — any POST to webhook endpoint is processed | Re-enable with proper key rotation |
| Stale Razorpay orders not cancelled | No cleanup job implemented | Orphaned orders in Razorpay dashboard | Add scheduled cleanup Lambda |
| OCE amount not tracked per-payment | Original design assumed 1:1 payment:order | Can't audit which payment covered which OCE | P2 — add junction table |
| 1 paisa rounding tolerance | Pre-decimal-migration records have rounding | Reconciliation allows +/-1 paisa on old records | Will be removed after full data migration |
| MAX_TRANSFER_AMOUNT_IN_RUPEES = 5 | Test transfer feature limit | Looks confusingly low — actually only for test transfers, not production | Add code comment; production limit is 19 crore |

## OCE Amount Field Usage Guide

| Field | Context | Example |
|---|---|---|
| `effective_amount` | Razorpay order creation (charging applicant) | `entity.effective_amount if entity.effective_amount is not None else entity.total_amount` |
| `revised_amount` | Fee consolidation, refunds, reconciliation ATR | `revised_amount if revised_amount is not None else amount` |
| `amount` | Base reference only — never use alone for business logic | Original fee_engine amount at order creation |

> These are NOT a precedence chain. Each is authoritative in its own context. Using the wrong field in the wrong context = wrong money.

## Entity Relationship Summary

```
Application (bps)
  └── Order (1:many, allow_partial=True for fee engine, False for direct)
        ├── OCE (1:many) — fee components (applicant can pay selected OCEs)
        ├── RazorpayOrder (1:many) — one per payment attempt, tracks which OCEs
        │     └── RazorpayOrderContributedEntity (junction) — links RzpayOrder to OCEs
        └── Payment (via RazorpayOrder, 1:many)
              └── PaymentRefund (1:many)

Application
  ├── ApplicationRefund (1:many) — refund requests
  ├── ReconciliationTransaction (1:many) — bank transfers
  └── ApplicationFeeConsolidation (1:many) — financial snapshots

TDR (non-monetary payment)
  └── TDROrder — certificate-based payment, separate lifecycle
        └── TDRRequest — verification with GHMC/HMDA authorities

Reconciliation Hierarchy
  ReconciliationRequest (batch CSV upload by business team)
    └── ApplicationReconciliation (per-app cycle, multiple cycles per app)
          └── ReconciliationTransaction (actual bank transfer via ICICI API)
```

## Status Enum Quick Reference

| Enum | Values | Notes |
|---|---|---|
| `OrderStatus` | YET_TO_PAY, PAID, PARTIALLY_PAID, CANCELLED, INITIATED, PROCESSING | PARTIALLY_PAID is derived |
| `PaymentStatus` | CREATED, AUTHORIZED, PAID, FAILED, INITIATED, UNDER_REVIEW, CANCELLED, REFUNDED | Razorpay `captured` = internal `PAID` |
| `OrderContributedEntityStatus` | YET_TO_PAY, PAID, PARTIALLY_PAID, FAILED | Per-OCE status |
| `RefundStatus` | INITIATED, PENDING, PROCESSED, FAILED | Per-payment refund |
| `ApplicationRefundStatus` | YET_TO_REFUND, IN_PROGRESS, COMPLETED, FAILED, PARTIALLY_FAILED | App-level refund |
| `ReconciliationRequestStatus` | PREVIEW_GENERATION_*, APPROVED_FOR_INITIATION, QUEUED, IN_PROGRESS, COMPLETED, PARTIALLY_FAILED, FAILED, DISCARDED | Batch level |
| `ApplicationReconciliationStatus` | DRAFT, DRAFT_VERIFIED, PENDING, IN_PROGRESS, DEBIT_CONFIRMED, CREDIT_PAID, SUCCESS, FAILED, REFUNDED, ERROR | Per-app cycle |
| `ReconciliationTransactionStatus` | DRAFT → DRAFT_VERIFIED → INITIATED → SUCCESSFULLY_DEBITED → POSTED_TO_RBI → WAITING_FOR_BENE → SUCCESSFULLY_CREDITED / FAILED / REFUNDED | Per-txn |
| `TDROrderStatus` | YET_TO_PAY, UNDER_VERIFICATION, PAID, CANCELLED | Certificate payment |
| `TDRRequestStatus` | DRAFT, CERTIFICATE_VALIDATED, CERTIFICATE_OWNERSHIP_VERIFIED, INITIATED, CONFIRMED, ACCEPTED | Verification flow |

## Revenue Protection Matrix

| Risk | Guard | Key | TTL |
|---|---|---|---|
| Double webhook processing | Redis lock | `RZPAY_WEBHOOK_ORDER_LOCK-{order_id}` | 600s |
| Duplicate Razorpay order | Redis lock | `CREATE_RAZORPAY_ORDER_IN_PORTAL-{order_id}` | 120s |
| Concurrent order refund | Redis lock | `REFUND_ORDER_LOCK-{order_id}` | 600s |
| Concurrent app refund | Redis lock | `APPLICATION_REFUND_LOCK-{application_id}` | 900s |
| Concurrent recon processing | Redis lock | `RECON_PROCESSING:{application_id}` | 120s |
| Concurrent recon draft | Redis lock | `GENERATE_RECONCILIATION_DRAFT-{pipeline_item_id}` | 120s |
| Duplicate TDR order | Redis lock | `CREATE_TDR_ORDER_IN_PORTAL-{order_id}` | 120s |
| Order status sync race | Redis lock | `SYNC_ORDER_STATUS_LOCK-{order_id}` | 120s |
| Invalid status transition | Config guard | `RZPAY_ORDER_DISALLOWED_STATUS_TRANSITIONS_CONFIG` | N/A |
| Invalid payment transition | Config guard | `PAYMENT_DISALLOWED_STATUS_TRANSITIONS_CONFIG` | N/A |
| Partial writes | DB guard | `@transaction.atomic` | N/A |
| Duplicate records | DB guard | Unique constraints on razorpay IDs | N/A |

## Cross-App Data Flow

```
fee_engine (calculates fees, AFH in rupees)
  → payments_engine (converts to paise, creates orders + OCEs)
    → Razorpay (processes payment in paise) OR TDR certificate (no money)
      → payments_engine (webhook: updates status, records payment)
        → payments_engine (reconciliation: ATR calculation, bank transfer)
          → ICICI Bank API (NEFT/RTGS transfer)
              → Status checks: debit (48 attempts, 30min) then credit (60 attempts, 120min)
```

## Key Metrics to Monitor

| Metric | Alert Threshold | Why |
|---|---|---|
| Webhook processing time | > 5s | Lock contention or DB bottleneck |
| Double-webhook rate | > 0.1% | Razorpay retry storm or lock failure |
| Selective payment rate | Track only | Understand partial payment patterns |
| Refund rejection rate | Sudden spike | Possible config issue or permission change |
| Reconciliation ATR delta | != 0 (beyond tolerance) | Data integrity issue |
| Recon cycle count per app | > 5 | Unusual — investigate why so many cycles |
| TDR verification time | > 48h | GHMC/HMDA bottleneck |
