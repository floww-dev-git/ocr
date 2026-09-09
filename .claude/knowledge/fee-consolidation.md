# ApplicationFeeConsolidation — Complete Knowledge

## What It Is

Per-fee-header financial snapshot for an application. Rebuilt from scratch (delete + recreate) every time via `@transaction.atomic`. Single source of truth for "how much collected, refunded, net remaining" — consumed by ATR calculation for reconciliation.

**Model:** `payments_engine/models/fee_consolidation.py`
**Interactor:** `payments_engine/interactors/application_fee_consolidation.py`

## Fields & Formulas (verified from interactor lines 194-218)

| Field | Formula | Type | Notes |
|---|---|---|---|
| `base_amount` | Sum of PAID **non-TDR** OCE amounts | Decimal(21,2) rupees | Uses `revised_amount ?? total_amount` per OCE |
| `penalty_amount` | Sum of PAID OCE `penalty_amount` | Decimal(21,2) rupees | Includes penalties on BOTH TDR and non-TDR OCEs |
| `tdr_amount` | Sum of PAID **TDR** OCE base amounts | Decimal(21,2) rupees | TDR OCEs go here, NOT into base_amount |
| `collected_amount` | `base_amount + penalty_amount` | Decimal(21,2) rupees | Excludes TDR (no real money collected for TDR) |
| `refunded_amount` | Sum of `FeeHeaderRefund.refund_amount` | Decimal(21,2) rupees | Includes ALL refund statuses (see gotcha below) |
| `net_amount` | `collected_amount - refunded_amount` | Decimal(21,2) rupees | **This is what ATR uses for reconciliation** |
| `fee_amount` | `collected_amount + tdr_amount` | Decimal(21,2) rupees | Total fee value including TDR |
| `category` | FEE_HEADER or EXTRA_AMOUNT_PAID | CharField | FEE_HEADER = one row per fee_header_id |
| `fee_header_id` | Fee header UUID or NULL | CharField(nullable) | NULL for EXTRA_AMOUNT_PAID category |

## OCE Amount Field Used: `revised_amount ?? total_amount`

```python
# Line 275-280 of application_fee_consolidation.py
@staticmethod
def _get_entity_base_amount(entity) -> int:
    return (
        entity.revised_amount
        if entity.revised_amount is not None
        else entity.total_amount
    )
```

**Field mapping:** `OrderContributedEntityDTO.total_amount` = `OrderContributedEntity.amount` (model field). The DTO field is named `total_amount` but it maps to the model's `amount` column. Do NOT rename the DTO field.

This is NOT `effective_amount` — consolidation uses `revised_amount` (fee recalculation adjusted) while Razorpay order creation uses `effective_amount` (setoff adjusted). Different fields for different contexts.

## Paise → Rupees Conversion

All OCE amounts arrive in paise (int). Consolidation converts at the boundary:
```python
@staticmethod
def _convert_paises_to_decimal_rupees(paises: int) -> Decimal:
    return Decimal(paises) / Decimal("100.00")
```

After this conversion, all consolidation fields are in Decimal rupees.

## TDR Separation Logic

OCEs are checked against paid TDR order OCE IDs:
- If OCE id is in `paid_tdr_oce_ids` → base amount goes to `tdr_amount`
- If OCE id is NOT in paid_tdr_oce_ids → base amount goes to `base_amount`
- **Penalty always goes to `penalty_amount`** regardless of TDR — penalty is always monetary

## EXTRA_AMOUNT_PAID (Catchall Row)

Created when `sum(net_amounts) != total_paid_razorpay - total_refunded`:
- `fee_header_id = NULL`
- `category = EXTRA_AMOUNT_PAID`
- `base_amount = extra_amount` (the discrepancy)
- All other fields = 0 or the extra amount
- Covers: rounding differences, unmapped fee heads, overpayments

## Validation (Post-Build Check)

```python
total_net_amount = sum(dto.net_amount for dto in consolidation_dtos)
expected_net_amount = total_paid_amount - total_refund_amount

if total_net_amount != expected_net_amount:
    raise ApplicationFeeConsolidationMismatchError(...)
```

`total_paid_amount` comes from **paid RazorpayOrders** (what was actually charged via Razorpay), NOT from OCE amounts. This is the ground truth of actual money received.

## Critical Gotcha: Refunded Amounts Include Non-Completed Refunds

Refund statuses included in `refunded_amount`:
- `YET_TO_REFUND` — refund approved but not yet initiated
- `IN_PROGRESS` — refund initiated with Razorpay
- `COMPLETED` — refund processed
- `FAILED` — refund failed
- `PARTIALLY_FAILED` — some payment refunds failed

Only `NON_REFUNDABLE` is excluded.

**This means `net_amount` reflects INTENDED refunds, not just completed ones.** A failed refund still reduces net_amount. This is by design — the intent to refund is captured immediately, and the business team handles failed refund recovery separately.

**No double-counting risk:** When a refund fails and is re-initiated, `FeeHeaderRefund` records are UPDATED (not new records). Only `PaymentRefund` (Razorpay-level) creates new records on retry. Since consolidation depends on `FeeHeaderRefund`, there's no double-counting.

**Impact on reconciliation:** ATR uses `net_amount`, so a failed refund reduces the amount available for reconciliation even though the money wasn't actually returned. The business team must resolve failed refunds to correct the numbers.

## EXTRA_AMOUNT_PAID — When and Why

**Real-world cause:** Applicant pays amount-X for a fee header in one order. Later, an officer revises the fee header amount to amount-Y where Y < X. The fee header is now overpaid. The overpaid difference has no fee_header to map to, so it goes into the `EXTRA_AMOUNT_PAID` catchall row.

This row:
- `fee_header_id = NULL`
- `category = EXTRA_AMOUNT_PAID`
- Aggregates ALL such overpayment discrepancies across all fee headers into a single row
- Is a normal business scenario, NOT an error — agents should never try to "fix" or prevent it
- Gets reconciled via `DIRECT_ORDER` config type (not FEE_HEADER)

## Validation Math: Why TDR Doesn't Break It

The validation check: `sum(net_amount) == total_paid_razorpay - total_refunded`

TDR is excluded from BOTH sides:
- Left side: `net_amount = collected_amount - refunded_amount` where `collected_amount = base_amount + penalty_amount` (TDR base goes to `tdr_amount`, not `base_amount`)
- Right side: `total_paid_razorpay` comes from paid RazorpayOrders — TDR payments have no RazorpayOrder

**BUT:** TDR penalty amounts DO go into `penalty_amount` → `collected_amount` → `net_amount`. If a TDR OCE has a penalty, that penalty IS real money (paid via Razorpay, not certificate). So TDR penalty is correctly on both sides: in `collected_amount` AND in `total_paid_razorpay` (the penalty was paid through a RazorpayOrder).

## Rebuild Behavior

1. Delete ALL existing consolidation rows for the application
2. Recalculate from source data (OCEs, refunds, RazorpayOrders)
3. Create new rows
4. All within `@transaction.atomic` — no partial state

This means consolidation is always fresh and consistent. No stale data possible. But it also means it's a relatively expensive operation (multiple DB reads + delete + bulk create).

## Data Sources

| Data | Source | Filtered By |
|---|---|---|
| Orders | `get_orders_for_entity_id(application_id)` | Statuses: YET_TO_PAY, PAID, PARTIALLY_PAID, INITIATED, PROCESSING (NOT CANCELLED) |
| OCEs | `get_order_contributed_entities_for_order_ids_by_statuses()` | Status: PAID only |
| TDR OCEs | `get_tdr_order_ids_for_order_ids()` + `get_tdr_oce_ids_for_tdr_order_ids()` | TDR status: PAID only |
| Refunds | `get_fee_header_refunds_by_application_refund_ids_by_statuses()` | All statuses except NON_REFUNDABLE |
| Total paid | `get_paid_razorpay_orders_by_order_ids()` | RazorpayOrder status: PAID |

## Downstream Consumers

- **ATR Calculation** (`CalculateAtrInteractor`) — uses `net_amount` per fee_header to determine reconciliation amounts
- **Reconciliation Preview** — displayed to business team before approval
- **Data Checks** — `payments_to_consolidation_checker.py` validates consistency
