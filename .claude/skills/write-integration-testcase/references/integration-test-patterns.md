# Integration Test Patterns Reference

## Core Principle: No Mocks for Cross-App Services

Integration tests populate ALL dependent apps' DB models directly. Instead of mocking `get_service_adapter().fee_engine`, create real `FeeRuleSet`, `FeeHeader`, `EntityFeeRuleSet`, `AppliedFeeHeader` records so the service reads from real DB.

Only mock truly external APIs (Razorpay, S3, webhooks) — never mock cross-app `app_interfaces`.

## DjangoModelFactory for Test Data

Integration tests use `DjangoModelFactory` (NOT `factory.Factory`) because records must exist in the real DB.

```python
import factory
from payments_engine.models import Order, OrderContributedEntity

class OrderFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Order

    entity_id = factory.Sequence(lambda n: f"app_{n}")
    status = OrderStatus.CREATED.value
    order_amount = 100000  # paise
    order_currency = "INR"

class OrderContributedEntityFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = OrderContributedEntity

    order = factory.SubFactory(OrderFactory)
    amount = 50000
    status = OrderContributedEntityStatus.CREATED.value
```

**Rules:**
- Inherit from `factory.django.DjangoModelFactory` for all model factories
- Use `factory.SubFactory()` for ForeignKey relationships
- Use `factory.Sequence()` for unique fields
- Use `.value` for enum fields
- Use `factory.LazyFunction()` for JSON fields (e.g., `json.dumps(...)`)
- Check `<app>/tests/factories/models.py` before creating — never duplicate

## Creating Model Factories for Apps That Lack Them

When a Django app has no model factories, create them in `<app>/tests/factories/models.py`. Handle these patterns:

```python
import json
import factory
from fee_engine.constants.enum import (
    EntityFeeRuleSetStatus,
    FeeHeaderExecType,
    FeeRuleSetEntity,
)
from fee_engine.models.entity_fee_rule_set import (
    AppliedFeeHeader,
    EntityFeeRuleSet,
    EntityFeeRuleSetOrder,
)
from fee_engine.models.fee_rule_set import FeeHeader, FeeRuleSet


class FeeRuleSetFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = FeeRuleSet

    id = factory.Sequence(lambda n: f"frs_{n}")
    name = factory.Sequence(lambda n: f"Fee Rule Set {n}")
    entity_type = FeeRuleSetEntity.PIPELINE_TEMPLATE.value
    entity_id = factory.Sequence(lambda n: f"template_{n}")


class FeeHeaderFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = FeeHeader

    id = factory.Sequence(lambda n: f"fh_{n}")
    name = factory.Sequence(lambda n: f"Fee Header {n}")
    fee_rule_set = factory.SubFactory(FeeRuleSetFactory)  # FK
    exec_type = FeeHeaderExecType.DEFAULT.value
    order = 1


class EntityFeeRuleSetFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = EntityFeeRuleSet

    id = factory.Sequence(lambda n: f"efrs_{n}")
    fee_rule_set = factory.SubFactory(FeeRuleSetFactory)  # FK
    entity_id = factory.Sequence(lambda n: f"app_{n}")
    status = EntityFeeRuleSetStatus.ORDERS_CREATED.value
    orders_created_at = None


class EntityFeeRuleSetOrderFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = EntityFeeRuleSetOrder

    entity_fee_rule_set = factory.SubFactory(EntityFeeRuleSetFactory)  # FK
    order_id = factory.Sequence(lambda n: f"order_{n}")
    creation_config = factory.LazyFunction(  # JSON field
        lambda: json.dumps({
            "fee_header_ids": [],
            "order_details": {"name": "Test Order", "allow_partial": False},
        })
    )
```

**Key patterns when creating factories:**
- `SubFactory` for every FK relationship — ensures parent records exist
- `LazyFunction` with `json.dumps()` for JSON/JSONB fields
- `Sequence` for fields with unique constraints
- `.value` for every enum/choice field (validators expect the string value, not the enum)

## Factory Location Convention

```
<app>/tests/factories/
    models.py              # DjangoModelFactory classes for this app's models
    interactors/           # factory.Factory classes for DTOs (unit tests only)
```

Integration tests import from `<app>/tests/factories/models.py`.

## FK Chain Setup (Critical for Multi-App Tests)

Integration tests often span multiple apps. Trace the full FK chain and create records top-down:

### Example: Fee Data Checks (fee_engine + payments_engine)

```
fee_engine (create first — upstream):
  FeeRuleSet
  └── FeeHeader (FK → FeeRuleSet)
  └── EntityFeeRuleSet (FK → FeeRuleSet)
      └── AppliedFeeHeader (FK → EntityFeeRuleSet, FK → FeeHeader)

payments_engine (create second — downstream):
  Order
  └── OrderContributedEntity (FK → Order)
  └── RazorpayOrder (FK → Order)
      └── Payment (FK → RazorpayOrder)
      └── RazorpayOrderContributedEntity (FK → RazorpayOrder, FK → OCE)

cross-app link:
  EntityFeeRuleSetOrder (FK → EntityFeeRuleSet, stores order_id as string)
```

In code:
```python
# 1. Fee engine records (parent → child)
frs = FeeRuleSetFactory(id="frs-hp-1")
fh = FeeHeaderFactory(id="fh-hp-1", fee_rule_set=frs)
efrs = EntityFeeRuleSetFactory(
    id="efrs-hp-1", fee_rule_set=frs,
    entity_id=APP_ID, orders_created_at=NOW,
)
AppliedFeeHeaderFactory(
    entity_fee_rule_set=efrs, fee_header=fh,
    amount_calculated_by_system=100.0, net_amount=100.0,
)

# 2. Payments engine records (parent → child)
order = OrderFactory(
    id="order-hp-1", entity_id=APP_ID,
    amount=10000, status=OrderStatus.PAID.value,
)
EntityFeeRuleSetOrderFactory(
    entity_fee_rule_set=efrs, order_id=order.id,
)
oce = OrderContributedEntityFactory(
    id="oce-hp-1", order=order,
    entity_type="FEE_HEAD", entity_id=fh.id,
    amount=10000, penalty_amount=0,
    status=OrderContributedEntityStatus.PAID.value,
)
rzp = RazorpayOrderFactory(
    razorpay_order_id="rzp-hp-1", order=order,
    amount=10000, status=RazorpayOrderPaymentStatus.PAID.value,
)
PaymentFactory(
    id="pay-hp-1", order=order,
    razorpay_order=rzp, amount=10000,
    status=PaymentStatus.PAID.value,
)
RazorpayOrderContributedEntityFactory(
    razorpay_order=rzp, order_contributed_entity=oce,
)
```

## Unique ID Prefixes

Each test file uses unique prefixes for all IDs to avoid DB collisions:

| Test file | Prefix | Example IDs |
|---|---|---|
| `test_happy_path.py` | `hp` | `"app-hp-1"`, `"frs-hp-1"`, `"order-hp-1"` |
| `test_amount_mismatch.py` | `amm` | `"app-disc-amm-1"`, `"frs-amm-1"` |
| `test_missing_oce.py` | `moce` | `"app-disc-moce-1"`, `"frs-moce-1"` |
| `test_recon_happy_path.py` | `rhp` | `"app-recon-hp-1"`, `"order-rhp-1"` |

Convention: `<entity_short>-<test_prefix>-<number>` (e.g., `"frs-hp-1"`, `"oce-amm-1"`).

## Amount Domain Rules

Financial tests must respect different amount units across apps:

| Domain | Unit | Type | Models |
|---|---|---|---|
| Payments engine | Paise (int) | `int` | Order.amount, OCE.amount, RazorpayOrder.amount, Payment.amount |
| Fee engine | Rupees | `float` | AppliedFeeHeader.amount_calculated_by_system, .net_amount |
| Consolidation | Rupees | `Decimal` | ApplicationFeeConsolidation.base_amount, .collected_amount, .net_amount |
| Reconciliation | Rupees | `Decimal` | ReconciliationTransaction.amount_in_rupees, TCE.amount_in_rupees |

**Conversion:** 1 rupee = 100 paise. AFH `net_amount=100.0` corresponds to OCE `amount=10000`.

```python
# Correct: matching amounts across domains
AppliedFeeHeaderFactory(net_amount=100.0)         # 100 rupees
OrderContributedEntityFactory(amount=10000)        # 10000 paise = 100 rupees
ApplicationFeeConsolidationFactory(
    collected_amount=Decimal("100.00"),             # 100 rupees as Decimal
)
```

## Test File Structure

```python
"""
Integration test: <SCENARIO> — <brief description>.
"""
import datetime

import pytest

from fee_engine.tests.factories.models import (
    AppliedFeeHeaderFactory,
    EntityFeeRuleSetFactory,
    FeeHeaderFactory,
    FeeRuleSetFactory,
)
from payments_engine.constants.enum import OrderStatus
from payments_engine.interactors.data_checks.orders_check.orders_check_interactor import (
    OrdersCheckInteractor,
)
from payments_engine.tests.factories.models import (
    OrderContributedEntityFactory,
    OrderFactory,
)

from integration_tests.fee_data_checks.common_fixtures import make_storage

APP_ID = "app-scenario-1"
NOW = datetime.datetime(2026, 1, 15, 12, 0, 0)


@pytest.mark.django_db
class TestScenarioName:
    """Integration tests for <scenario description>."""

    def test_description(self):
        """
        Docstring: describe data setup and expected outcome.
        """
        # Arrange — fee engine records
        # ... create parent-to-child

        # Arrange — payments engine records
        # ... create parent-to-child

        # Act
        results = OrdersCheckInteractor(
            storage=make_storage()
        ).run_checks_for_applications(application_ids=[APP_ID])

        # Assert
        assert len(results) == 1
        result = results[0]
        assert result.has_discrepancy is False
```

## Asserting Discrepancies

```python
# Assert specific discrepancy type exists
result = results[0]
assert result.has_discrepancy is True
matching = [
    d for d in result.discrepancies
    if d.discrepancy_type == OrdersDiscrepancyType.AMOUNT_MISMATCH.value
]
assert len(matching) >= 1
assert matching[0].expected_value == 10000
assert matching[0].stored_value == 9999
```

## Asserting DB State Changes

### Verify record was updated
```python
order.refresh_from_db()
assert order.status == OrderStatus.PAID.value
```

### Verify records were created
```python
from app.models import AuditLog
logs = list(AuditLog.objects.filter(entity_id=order.id))
assert len(logs) == 1
assert logs[0].action == "PROCESSED"
```

### Verify count and aggregates
```python
from payments_engine.models import ApplicationFeeConsolidation
consolidations = ApplicationFeeConsolidation.objects.filter(
    application_id="app-1"
)
total = sum(c.collected_amount for c in consolidations)
assert total == Decimal("300.00")  # 30000 paise -> 300 rupees
```

## Mocking Truly External APIs Only

Only mock services that call external APIs (Razorpay, S3, etc.):

```python
from unittest.mock import patch, PropertyMock, Mock

class TestWithExternalService:

    @patch(
        "payments_engine.interactors.process_payment.ProcessPaymentInteractor"
        ".razorpay_service",
        new_callable=PropertyMock,
    )
    def test_processes_payment(self, mock_razorpay_prop, interactor):
        # Arrange
        mock_service = Mock()
        mock_razorpay_prop.return_value = mock_service
        mock_service.capture_payment.return_value = CaptureResultDTO(
            status="captured"
        )
        order = OrderFactory(status=OrderStatus.AUTHORIZED.value)

        # Act
        result = interactor.capture(order_id=order.id)

        # Assert
        order.refresh_from_db()
        assert order.status == OrderStatus.PAID.value
```

## Deterministic Datetime

```python
from freezegun import freeze_time

@pytest.mark.django_db
@freeze_time("2025-01-15 10:00:00")
class TestTimeDependentFeature:

    def test_due_date_calculation(self, interactor):
        order = OrderFactory(due_datetime=datetime(2025, 1, 10, 10, 0, 0))
        result = interactor.check_overdue()
        assert result.is_overdue is True
        assert result.days_overdue == 5
```

## common_fixtures.py — Keep It Minimal

The common_fixtures file should contain ONLY truly shared utilities:

```python
"""
Common fixtures and utilities for <feature> integration tests.

All data setup uses real model factories — no service mocks.
"""
from payments_engine.storages.data_checks_storage import DataChecksStorage


def make_storage() -> DataChecksStorage:
    return DataChecksStorage()
```

No mock classes, no patch helpers, no DTO factories. Each test file imports its own factories directly from source apps.

## Anti-Patterns (Do NOT Do)

```python
# BAD: Mocking cross-app services — populate their DB instead
fee_mock = FeeEngineMock(efrs_by_app={...})  # NEVER — create real DB records

# BAD: Mocking storage in integration tests
storage = create_autospec(StorageInterface)  # NEVER in integration tests

# BAD: Asserting mock calls instead of DB state
storage.update_order.assert_called_once_with(...)  # NEVER

# BAD: Using factory.Factory for models (creates Python objects, not DB records)
class OrderDTOFactory(factory.Factory):  # WRONG for integration tests
    class Meta:
        model = Order  # This does NOT hit the DB

# BAD: Using Model.objects.create() directly
Order.objects.create(id="o1", amount=100)  # Use OrderFactory instead

# BAD: Shared mutable state across tests
class TestSuite:
    shared_order = None  # NEVER — each test creates its own data

# BAD: Defining factories locally in test files
class LocalOrderFactory(factory.django.DjangoModelFactory):  # NEVER
    class Meta:
        model = Order  # Put this in payments_engine/tests/factories/models.py

# BAD: Mixing paise and rupees
AppliedFeeHeaderFactory(net_amount=10000)  # WRONG — this is rupees, not paise
OrderContributedEntityFactory(amount=100)  # WRONG — this is paise, not rupees
```

## Test Naming Convention

| Scenario | Pattern |
|---|---|
| Happy path | `test_<operation>_with_valid_data` or `test_no_discrepancies_when_*` |
| Discrepancy detection | `test_<discrepancy_type>_discrepancy` |
| Missing prerequisite | `test_<operation>_when_<entity>_not_found` |
| Empty input | `test_<operation>_with_no_<entities>` |
| Edge case | `test_<operation>_with_<boundary_condition>` |

## Running Integration Tests

```bash
# Single test
pytest integration_tests/<feature>/test_<scenario>.py -v

# Full feature
pytest integration_tests/<feature>/ -v

# All integration tests
pytest integration_tests/ -v
```
