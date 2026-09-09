---
name: razorpay-integration
description: "Step-by-step workflow for implementing new Razorpay integration points — webhook handlers, payment flows, refund flows, order creation. Includes code patterns, error handling, and testing templates specific to this codebase's Razorpay setup."
disable-model-invocation: true
allowed-tools: Read, Grep, Glob, Write, Edit, Bash
---

# Razorpay Integration Guide

Follow this workflow when adding new Razorpay-dependent features to `payments_engine/`.

## Step 1: Understand the Existing Integration

Read these files before writing any code:
- `payments_engine/CLAUDE.md` — full domain context
- `payments_engine/interactors/razorpay_webhook_event.py` — webhook router
- `payments_engine/constants/` — status enums, transition configs
- `payments_engine/adapters/razorpay_service.py` — SDK wrapper and configuration

There is a SECOND, independent Razorpay surface in `ib_payments/` — its own SDK wrapper
(`ib_payments/adapters/razorpay_payment_service.py`) and its own inbound webhook view
(`ib_payments/razorpay_webhook_view.py`, routed at `webhook/ib_payments/`). This skill's patterns
are written for `payments_engine/`; if the work is in `ib_payments/`, read that app's code first —
do not assume the two share shapes.

## Step 2: Identify the Integration Point

| If you're adding... | Pattern to follow |
|---|---|
| New webhook event handler | Add handler in `interactors/razorpay_events/`, register in webhook router |
| New payment flow | Create interactor with lock + atomic, use existing `RazorpayOrder` model |
| New refund type | Extend refund validation chain, add to `ApplicationRefund` model |
| New order type | Extend `CreateOrdersInteractor`, ensure OCE atomicity |

## Step 3: Implement the Razorpay Call

### Order Creation Pattern
```python
from payments_engine.adapters.razorpay_adapter import RazorpayAdapter

class CreateRazorpayOrderInteractor:
    def __init__(self, storage: OrderStorageInterface):
        self.storage = storage

    @property
    def razorpay_adapter(self) -> RazorpayAdapter:
        return get_service_adapter().razorpay_service

    def execute(self, order_dto: OrderDTO) -> RazorpayOrderDTO:
        # Skip Razorpay for zero-amount orders
        if order_dto.amount_paise == 0:
            return self._auto_mark_paid(order_dto)

        razorpay_order = self.razorpay_adapter.create_order(
            amount=order_dto.amount_paise,  # Razorpay expects paise
            currency="INR",
            receipt=order_dto.id,
            notes={"order_id": order_dto.id},
        )
        return self.storage.create_razorpay_order(
            order_id=order_dto.id,
            razorpay_order_id=razorpay_order["id"],
        )
```

### Webhook Handler Pattern
```python
class ProcessNewEventInteractor:
    def __init__(self, storage: PaymentStorageInterface):
        self.storage = storage

    def execute(self, event_data: dict) -> None:
        order_id = event_data["payload"]["order"]["entity"]["receipt"]
        lock_key = f"rzpay_webhook_lock:{order_id}"

        with redis_lock(lock_key, ttl=30):
            with transaction.atomic():
                # 1. Check idempotency — already processed?
                existing = self.storage.get_payment_by_razorpay_id(
                    event_data["payload"]["payment"]["entity"]["id"]
                )
                if existing:
                    return  # Idempotent — already handled

                # 2. Load order with row lock
                order = self.storage.get_order_for_update(order_id)

                # 3. Validate status transition
                self._validate_transition(order.status, target_status)

                # 4. Verify amount
                paid_amount = event_data["payload"]["payment"]["entity"]["amount"]
                if paid_amount != order.amount_paise:
                    return self._handle_amount_mismatch(order, paid_amount)

                # 5. Update status
                self.storage.update_order_status(order_id, target_status)
```

### Refund Pattern
```python
class InitiateRazorpayRefundInteractor:
    def execute(self, payment_id: str, amount_paise: int) -> RefundDTO:
        lock_key = f"application_refund_lock:{application_id}"

        with redis_lock(lock_key, ttl=120):
            # 1. Triple validation
            self._validate_application_eligibility(application_id)
            self._validate_order_refundability(order)
            refund_amount = self._calculate_refundable_amount(order, fee_configs)

            # 2. Initiate with Razorpay
            razorpay_refund = self.razorpay_adapter.create_refund(
                payment_id=payment.razorpay_payment_id,
                amount=refund_amount,  # paise
            )

            # 3. Record locally
            return self.storage.create_refund(
                payment_id=payment_id,
                razorpay_refund_id=razorpay_refund["id"],
                amount_paise=refund_amount,
            )
```

## Step 4: Error Handling

```python
# Razorpay SDK errors to catch
from razorpay.errors import (
    BadRequestError,    # 400 — invalid params
    ServerError,        # 500 — Razorpay down
    GatewayError,       # 502 — gateway issue
    SignatureVerificationError,  # webhook signature mismatch
)

try:
    result = razorpay_client.order.create(data)
except BadRequestError as e:
    raise InvalidRazorpayRequestError(detail=str(e))
except (ServerError, GatewayError) as e:
    raise RazorpayServiceUnavailableError(detail=str(e))
```

## Step 5: Write Tests

For every new Razorpay integration point, write tests covering:
1. **Happy path** — successful Razorpay call + local state update
2. **Idempotency** — duplicate call returns same result
3. **Razorpay failure** — SDK raises error, local state unchanged
4. **Amount mismatch** — paid != expected, PARTIALLY_PAID
5. **Lock contention** — Redis lock unavailable

Always mock `razorpay.Client` — never hit real Razorpay in tests.

## Step 6: Register (Webhooks Only)

If adding a new webhook event handler:
1. Add event type to `HANDLED_EVENTS` in `razorpay_webhook_event.py`
2. Register handler mapping in the event router
3. Add event to the list in `payments_engine/CLAUDE.md`
