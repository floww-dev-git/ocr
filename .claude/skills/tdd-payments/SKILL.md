---
name: tdd-payments
description: "TDD workflow for payments_engine — test-first patterns for payment flows, refunds, reconciliation, and webhooks. Covers idempotency tests, amount boundary tests, lock contention tests, and status transition tests. Use when writing tests for payments_engine features."
disable-model-invocation: true
allowed-tools: Read, Grep, Glob, Write, Edit, Bash
---

# TDD for Payments

Test-first workflow for `payments_engine/`. Write the test, watch it fail, implement, watch it pass.

## Step 1: Identify Test Scope

Read the interactor/feature being tested. For each, you MUST write tests in ALL these categories:

| Category | What it proves | Skip = bug risk |
|---|---|---|
| Happy path | Feature works correctly | Basic correctness |
| Idempotency | Duplicate calls are safe | Double-charges |
| Amount boundaries | Edge amounts handled | Wrong money |
| Lock contention | Concurrent access safe | Race conditions |
| Status transitions | State machine enforced | Invalid states |
| Failure paths | Errors handled gracefully | Silent failures |

## Step 2: Set Up Test Infrastructure

### Test File Location
```
payments_engine/tests/interactors/<sub_module>/test_<interactor_name>.py
```

### Base Test Setup
```python
import pytest
from decimal import Decimal
from unittest.mock import MagicMock, patch, PropertyMock
from dataclasses import dataclass

from payments_engine.dtos import OrderDTO, PaymentDTO, OCEDTO
from payments_engine.exceptions import (
    InvalidOrderStatusTransition,
    RefundLockUnavailableError,
)
from payments_engine.constants.enums import OrderStatus, PaymentStatus


class TestProcessPaymentInteractor:
    def setup_method(self):
        self.storage = MagicMock()
        self.interactor = ProcessPaymentInteractor(storage=self.storage)
```

### DTO Factories (not MagicMock)
```python
@dataclass
class OrderDTOFactory:
    @staticmethod
    def create(
        order_id: str = "order_001",
        amount_paise: int = 100000,
        status: str = OrderStatus.YET_TO_PAY.value,
        **overrides,
    ) -> OrderDTO:
        defaults = dict(
            id=order_id,
            amount_paise=amount_paise,
            status=status,
        )
        defaults.update(overrides)
        return OrderDTO(**defaults)
```

## Step 3: Write Tests (Category by Category)

### 3a. Happy Path
```python
def test_payment_captured_updates_order_to_paid(self):
    # Arrange
    order = OrderDTOFactory.create(status=OrderStatus.PAYMENT_INITIATED.value)
    self.storage.get_order_for_update.return_value = order
    self.storage.get_payment_by_razorpay_id.return_value = None

    # Act
    self.interactor.execute(payment_event_data)

    # Assert
    self.storage.update_order_status.assert_called_once_with(
        order.id, OrderStatus.PAID.value
    )
```

### 3b. Idempotency
```python
def test_duplicate_webhook_does_not_create_second_payment(self):
    # Arrange — payment already exists
    existing_payment = PaymentDTOFactory.create()
    self.storage.get_payment_by_razorpay_id.return_value = existing_payment

    # Act
    self.interactor.execute(payment_event_data)

    # Assert — no new payment created
    self.storage.create_payment.assert_not_called()
    self.storage.update_order_status.assert_not_called()
```

### 3c. Amount Boundaries
```python
def test_zero_amount_order_auto_marks_paid_without_razorpay(self):
    order = OrderDTOFactory.create(amount_paise=0)
    self.storage.get_order_for_update.return_value = order

    self.interactor.execute(order.id)

    self.storage.update_order_status.assert_called_with(
        order.id, OrderStatus.PAID.value
    )
    self.razorpay_adapter.create_order.assert_not_called()

def test_negative_oce_amount_is_valid_offset(self):
    oce = OCEDTOFactory.create(amount_paise=-50000, revised_amount=None)
    effective = oce.revised_amount if oce.revised_amount is not None else oce.amount_paise
    assert effective == -50000  # Valid, not an error

def test_amount_mismatch_sets_partially_paid(self):
    order = OrderDTOFactory.create(amount_paise=100000)
    self.storage.get_order_for_update.return_value = order

    event_data = self._create_event(paid_amount=80000)  # Mismatch
    self.interactor.execute(event_data)

    self.storage.update_order_status.assert_called_with(
        order.id, OrderStatus.PARTIALLY_PAID.value
    )

def test_paise_to_rupees_conversion_exact(self):
    assert Decimal(999999) / Decimal("100.00") == Decimal("9999.99")
    assert Decimal(1) / Decimal("100.00") == Decimal("0.01")
    assert Decimal(0) / Decimal("100.00") == Decimal("0.00")
```

### 3d. Lock Contention
```python
@patch("payments_engine.interactors.redis_lock")
def test_webhook_fails_gracefully_when_lock_unavailable(self, mock_lock):
    mock_lock.side_effect = LockError("Could not acquire lock")

    with pytest.raises(WebhookLockUnavailableError):
        self.interactor.execute(payment_event_data)

    self.storage.update_order_status.assert_not_called()
```

### 3e. Status Transitions
```python
@pytest.mark.parametrize(
    "current_status,target_status",
    [
        (OrderStatus.PAID.value, OrderStatus.YET_TO_PAY.value),
        (OrderStatus.PAID.value, OrderStatus.PAYMENT_INITIATED.value),
        (OrderStatus.FAILED.value, OrderStatus.PAID.value),
    ],
)
def test_disallowed_transitions_raise_exception(self, current_status, target_status):
    order = OrderDTOFactory.create(status=current_status)
    self.storage.get_order_for_update.return_value = order

    with pytest.raises(InvalidOrderStatusTransition):
        self.interactor._validate_transition(current_status, target_status)
```

### 3f. Failure Paths
```python
def test_razorpay_server_error_does_not_change_order_status(self):
    self.razorpay_adapter.create_order.side_effect = ServerError("503")
    order = OrderDTOFactory.create()

    with pytest.raises(RazorpayServiceUnavailableError):
        self.interactor.execute(order.id)

    self.storage.update_order_status.assert_not_called()
```

## Step 4: Run and Verify

```bash
# Run specific test file
pytest payments_engine/tests/interactors/<path>/test_<name>.py -v --no-migrations -x

# Run full payment suite
pytest payments_engine/tests/ -v --no-migrations

# With coverage
pytest payments_engine/tests/ --cov=payments_engine --cov-report=term-missing --no-migrations
```

## Step 5: Checklist Before Done

- [ ] Every test has Arrange/Act/Assert structure
- [ ] Factory Boy or @dataclass factories used (no MagicMock for DTOs)
- [ ] Razorpay SDK mocked (no real API calls)
- [ ] All 6 categories covered for each interactor
- [ ] Test names describe the business rule they protect
- [ ] No test depends on execution order
- [ ] All tests pass: `pytest payments_engine/tests/ -v --no-migrations`
