# Integration Test Templates

Skeletons for the SKILL.md's Step 4 (common_fixtures) and Step 6 (test file).
The Structural Rules and Quality Checklist in SKILL.md own the rules.

## common_fixtures.py template (Step 4)

Only truly shared utilities. Keep it minimal:

```python
"""
Common fixtures and utilities for <feature> integration tests.

All data setup uses real model factories — no service mocks.
Model factories imported from respective apps:
  - fee_engine/tests/factories/models.py
  - payments_engine/tests/factories/models.py
"""
from payments_engine.storages.data_checks_storage import DataChecksStorage


def make_storage() -> DataChecksStorage:
    return DataChecksStorage()
```

No mock classes, no patch helpers, no DTO factories. If a test needs to mock a truly
external API (Razorpay), do it inline in that test file.

## Test file template (Step 6) — one file per test case

```python
"""
Integration test: <SCENARIO_NAME> — <brief description>.
"""
import datetime

import pytest

from fee_engine.tests.factories.models import (
    AppliedFeeHeaderFactory,
    EntityFeeRuleSetFactory,
    EntityFeeRuleSetOrderFactory,
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

APP_ID = "app-scenario-1"  # Unique prefix per file
NOW = datetime.datetime(2026, 1, 15, 12, 0, 0)


@pytest.mark.django_db
class TestScenarioName:
    def test_description(self):
        """
        Docstring describing the data setup and expected outcome.
        """
        # Arrange — fee engine records (create parent-to-child)
        frs = FeeRuleSetFactory(id="frs-scenario-1")
        fh = FeeHeaderFactory(id="fh-scenario-1", fee_rule_set=frs)
        efrs = EntityFeeRuleSetFactory(
            id="efrs-scenario-1",
            fee_rule_set=frs,
            entity_id=APP_ID,
            orders_created_at=NOW,
        )
        AppliedFeeHeaderFactory(
            entity_fee_rule_set=efrs, fee_header=fh,
            amount_calculated_by_system=100.0, net_amount=100.0,
        )

        # Arrange — payments engine records
        order = OrderFactory(
            id="order-scenario-1", entity_id=APP_ID,
            amount=10000, status=OrderStatus.PAID.value,
        )
        EntityFeeRuleSetOrderFactory(
            entity_fee_rule_set=efrs, order_id=order.id,
        )

        # Act
        results = OrdersCheckInteractor(
            storage=make_storage()
        ).run_checks_for_applications(application_ids=[APP_ID])

        # Assert
        assert len(results) == 1
        result = results[0]
        assert result.has_discrepancy is False
```
