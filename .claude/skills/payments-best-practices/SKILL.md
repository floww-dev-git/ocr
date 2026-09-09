---
name: payments-best-practices
description: "Payment engineering best practices — Razorpay integration, idempotency patterns, amount handling (paise/rupees), distributed locking, status machine guards, refund safety. Use when working on payments_engine, fee_engine, or ib_payments."
disable-model-invocation: true
---

# Payments Best Practices

Rules for ALL code in `payments_engine/`, `fee_engine/`, and `ib_payments/`.

## 1. Amount Handling

| Context | Unit | Type | Example |
|---|---|---|---|
| Orders, OCEs, Payments | paise | `int` | `amount = 100000` (= 1,000.00 rupees) |
| Fee Engine AFH | rupees | `Decimal` | `amount = Decimal("1000.00")` |

### Conversion
```python
# Paise -> Rupees (ONLY at display/API boundary)
rupees = Decimal(paise) / Decimal("100.00")

# Rupees -> Paise
paise = int(rupees * 100)
```

### OCE Amount Fields — Context-Dependent (NOT a precedence chain)
| Field | Use in | Never use in |
|---|---|---|
| `effective_amount` | Razorpay order creation (what to charge) | Consolidation, refunds, recon |
| `revised_amount ?? amount` | Fee consolidation, refunds, reconciliation ATR | Razorpay order creation |
| `amount` alone | Never for business logic | Everywhere — always use effective or revised |

### Prohibited
- `float` for money — NEVER
- `round()` on paise — they're integers
- `amount_paise / 100` — use `Decimal("100.00")`
- Using wrong OCE amount field for the context (see table above)
- Filtering negative OCEs — they're valid fee revision offsets (setoff gives them `effective_amount=0`)

## 2. Idempotency

- Every payment mutation accepts `idempotency_key`
- Check existing record before creating — return existing if found
- Webhook handlers: same event twice = same outcome, zero duplicates
- DB unique constraints as final guard (`razorpay_payment_id`, `razorpay_order_id`)

## 3. Distributed Locks (Redis)

| Operation | Key (from `constants/config.py`) | TTL |
|---|---|---|
| Webhook processing | `RZPAY_WEBHOOK_ORDER_LOCK-{order_id}` | 600s |
| Razorpay order creation | `CREATE_RAZORPAY_ORDER_IN_PORTAL-{order_id}` | 120s |
| Refund (order-level) | `REFUND_ORDER_LOCK-{order_id}` | 600s |
| Refund (app-level) | `APPLICATION_REFUND_LOCK-{application_id}` | 900s |
| Recon processing | `RECON_PROCESSING:{application_id}` | 120s |
| Recon draft generation | `GENERATE_RECONCILIATION_DRAFT-{pipeline_item_id}` | 120s |
| Order status sync | `SYNC_ORDER_STATUS_LOCK-{order_id}` | 120s |
| TDR order creation | `CREATE_TDR_ORDER_IN_PORTAL-{order_id}` | 120s |

- ALWAYS acquire before critical section
- ALWAYS use the constant from `config.py` — never hardcode key strings
- NEVER reduce TTL below documented minimum
- Handle `LockError` gracefully — raise domain exception

## 4. Status Machine Guards

- OrderStatus: `YET_TO_PAY`, `PAID`, `PARTIALLY_PAID`, `CANCELLED`, `INITIATED`, `PROCESSING`
- PaymentStatus: `CREATED`, `AUTHORIZED`, `PAID`, `FAILED`, `INITIATED`, `UNDER_REVIEW`, `CANCELLED`, `REFUNDED`
- There is NO internal `CAPTURED`, `SUCCESS`, `PAYMENT_INITIATED`, or `REFUND_INITIATED` status
- Razorpay `captured` maps to internal `PAID` via `RazorpayPaymentStatus.get_payment_status()`
- `PARTIALLY_PAID` is derived — compare paid OCEs sum vs order amount, not a stored transition
- Check against `RZPAY_ORDER_DISALLOWED_STATUS_TRANSITIONS_CONFIG` and `PAYMENT_DISALLOWED_STATUS_TRANSITIONS_CONFIG`
- Disallowed transition -> raise domain exception (never silently ignore)
- Update `status_updated_at` on every transition
- Use `select_for_update()` when reading status before writing

## 5. Razorpay Integration

1. Validate webhook signature (currently DISABLED — P0 gap)
2. Acquire Redis lock: `RZPAY_WEBHOOK_ORDER_LOCK-{order_id}` (600s)
3. Parse event type and route to handler
4. Verify payment amounts match
5. Update status within `@transaction.atomic`
6. Applicant can pay selected OCEs only → unpaid OCEs remain, order derives PARTIALLY_PAID

## 6. Refund Safety

Triple validation chain (all must pass):
1. Application eligibility — no existing refund in progress, valid state, permission
2. Order refundability — only PAID non-TDR orders, not already fully refunded
3. Fee config check — `is_refundable` per fee header; non-refundable silently excluded

## 7. Reconciliation

Three-level hierarchy: ReconciliationRequest (batch CSV) → ApplicationReconciliation (per-app cycle) → ReconciliationTransaction (per-txn bank transfer)
- An application can have MULTIPLE recon cycles — reconcile ASAP as payments come in
- ATR = `Total Paid - Total Refunded - Already Reconciled`
- Production transaction limit: 19 crore/txn — auto-split above (NOT 5 rupees — that's the test transfer limit)
- TDR OCEs excluded from normal ATR (TDR = certificate, no money)
- 1 paisa tolerance ONLY for pre-migration records

## 8. TDR Awareness

TDR = non-monetary payment via government certificate. No Razorpay, no real money.
- ALWAYS exclude TDR OCEs from: refund calculations, ATR, consolidation base amounts
- TDR has its own status machine: `YET_TO_PAY` → `UNDER_VERIFICATION` → `PAID` → `CANCELLED`
- TDR authorities: GHMC, HMDA (Hyderabad government bodies)
- Treat TDR as a fundamentally different payment instrument, not "money we haven't collected"
