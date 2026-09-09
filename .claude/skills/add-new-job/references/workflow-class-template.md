# Workflow Class Template

Annotated template for a `BaseWorkflow` implementation. Every line has a comment explaining WHY.

## Workflow Class

File: `<owning_app>/workflows/<workflow_name>/workflow.py`

```python
from typing import Any, Dict

from jobs_engine.base.base_workflow import BaseWorkflow, operation  # BaseWorkflow extends BaseJob; @operation registers methods as state-machine steps
from jobs_engine.constants.enums import QueuePriority
from jobs_engine.registry.job_registry import register_job


@register_job                                       # Same decorator as regular jobs — adds to _REGISTRY at import time
class YourWorkflowName(BaseWorkflow):
    job_type = "<app>.<action>"                     # MUST match ^[a-z_]+\.[a-z_]+$ — same convention as regular jobs
    # noinspection PyTypeChecker
    queue_priority = QueuePriority.STANDARD.value   # Enum .value + noinspection comment
    max_retries = 0                                 # Retries are per-state in the ASL, not at the job level
    timeout_seconds = 3600                          # Total state machine timeout — longer than SQS jobs (15min Lambda limit doesn't apply)
    idempotency_fields = ()                         # Tuple of payload keys for dedup hash
    idempotency_window_hours = 24                   # How long to remember the dedup hash
    payload_schema = {                              # SchemaEngine-validated at publish time — gate bad data early
        "input_s3_url": {"type": "string", "required": True},
    }

    # --- env_config: per-environment state machine and Lambda ARNs ---
    # StepFunctionStrategy reads this to build the state machine ARN and start execution.
    # WorkflowStepFunction reads this for deployment (IAM role, state machine creation).
    # Keys: state_machine_name (required), lambda_function_arn (required), region (required).
    # Optional: step_functions_role_name, role_arn, state_machine_arn.
    @property
    def env_config(self) -> Dict[str, Dict[str, str]]:
        from django.conf import settings

        region = settings.AWS_DEFAULT_REGION
        account_id = settings.AWS_ACCOUNT_ID
        return {
            "gamma": {
                "state_machine_name": "YourWorkflowNameGamma",
                "lambda_function_arn": (
                    f"arn:aws:lambda:{region}:{account_id}:function:tg-build-now-bg-worker-gamma"
                ),
                "region": region,
            },
            "uat": {
                "state_machine_name": "YourWorkflowNameUat",
                "lambda_function_arn": (
                    f"arn:aws:lambda:{region}:{account_id}:function:tg-build-now-bg-worker-uat"
                ),
                "region": region,
            },
            "prod": {
                "state_machine_name": "YourWorkflowNameProd",
                "lambda_function_arn": (
                    f"arn:aws:lambda:{region}:{account_id}:function:tg-build-now-bg-worker-prod"
                ),
                "region": region,
            },
        }

    # --- get_state_machine_definition: returns ASL JSON dict ---
    # Called by WorkflowStepFunction for deployment and dry-run preview.
    # Delegates to a separate state_machine.py module for readability.
    def get_state_machine_definition(self) -> Dict[str, Any]:
        from django.conf import settings

        from step_functions.config import StepFunctionConfig

        from .state_machine import get_your_workflow_json  # Co-located ASL definition

        stage_config = self.env_config.get(settings.STAGE, {})
        lambda_function_arn = stage_config.get("lambda_function_arn", "")
        config = StepFunctionConfig(
            step_function_name=self.job_type,
            lambda_function_arn=lambda_function_arn,
            timeout_seconds=self.timeout_seconds,
        )
        return get_your_workflow_json(config=config)

    # --- @operation methods: one per state machine Task state ---
    # Each method is called by step_function_handler via dispatch_operation().
    # The handler routes based on the "operation" field in the Lambda event.
    # Rules:
    #   - Lazy imports inside each method (avoid circular dependencies)
    #   - Receives event: Dict[str, Any] (the full Lambda event)
    #   - Returns Dict[str, Any] (stored in ResultPath in ASL)
    #   - Instantiate interactors with storage constructors — same as GraphQL mutate()
    #   - Extract fields from event dict — these come from ASL Parameters.$

    @operation(name="init_job")
    def init_job(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """First step: validate input, prepare work items, seed progress."""
        from <owning_app>.interactors.<module>.init_interactor import (
            InitInteractor,
        )
        from jobs_engine.storages.job_execution_storage import (
            JobExecutionStorage,
        )

        interactor = InitInteractor(
            job_execution_storage=JobExecutionStorage(),
        )
        return interactor.execute(
            job_id=event["job_id"],
            payload=event["payload"],
            execution_arn=event["execution_arn"],
        )

    @operation(name="process_batch")
    def process_batch(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Map iterator step: process one batch/item."""
        from <owning_app>.interactors.<module>.process_interactor import (
            ProcessInteractor,
        )
        from <owning_app>.storages.some_storage_impl import SomeStorage

        interactor = ProcessInteractor(
            some_storage=SomeStorage(),
        )
        interactor.execute(
            job_id=event["job_id"],
            batch_key=event["batch_key"],
        )
        return {}

    @operation(name="record_batch_failure")
    def record_batch_failure(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Per-batch error handler: record failure details for observability."""
        from <owning_app>.interactors.<module>.record_failure_interactor import (
            RecordFailureInteractor,
        )
        from jobs_engine.storages.job_execution_storage import (
            JobExecutionStorage,
        )

        interactor = RecordFailureInteractor(
            job_execution_storage=JobExecutionStorage(),
        )
        interactor.execute(
            job_id=event["job_id"],
            batch_key=event["batch_key"],
            error=event.get("error", {}),
        )
        return {}

    @operation(name="finalize")
    def finalize(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Final step: aggregate results, update job status, clean up."""
        from <owning_app>.interactors.<module>.finalize_interactor import (
            FinalizeInteractor,
        )
        from jobs_engine.storages.job_execution_storage import (
            JobExecutionStorage,
        )

        interactor = FinalizeInteractor(
            job_execution_storage=JobExecutionStorage(),
        )
        interactor.execute(
            job_id=event["job_id"],
            batch_keys=event["batch_keys"],
        )
        return {}

    @operation(name="handle_error")
    def handle_error(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Global error handler: mark job FAILED, record error details."""
        from <owning_app>.interactors.<module>.handle_error_interactor import (
            HandleErrorInteractor,
        )
        from jobs_engine.storages.job_execution_storage import (
            JobExecutionStorage,
        )

        interactor = HandleErrorInteractor(
            job_execution_storage=JobExecutionStorage(),
        )
        interactor.execute(
            job_id=event["job_id"],
            error=event.get("error", {}),
        )
        return {}
```

## Key Differences from BaseJob

| Aspect | BaseJob (SQS) | BaseWorkflow (Step Functions) |
|--------|---------------|-------------------------------|
| Base class | `BaseJob` | `BaseWorkflow` (extends `BaseJob`) |
| `backend_type` | `BackendType.QUEUE.value` (default) | `BackendType.STEP_FUNCTION.value` (inherited, do NOT set explicitly) |
| Entry point | `execute(context) -> JobResult` | `@operation` methods, each `(event) -> dict` |
| `execute()` | Your implementation | Raises `NotImplementedError` — do NOT override |
| Error handling | `PermanentFailure`/`TransientFailure` | Per-state Retry/Catch in ASL + `handle_error` operation |
| Timeout | Lambda 15min limit | State machine `TimeoutSeconds` (can be hours) |
| Parallelism | None (single Lambda) | ASL Map state with `MaxConcurrency` |
| File location | `<app>/jobs/` | `<app>/workflows/<workflow_name>/` |
| Additional files | None | `state_machine.py` (ASL definition) |
| Return value | `JobResult` | `dict` (stored in ASL `ResultPath`) |
| Status after start | `SUCCESS` or `FAILED` | `IN_PROGRESS` (Step Functions runs asynchronously) |

## Canonical Example

`automation_workflows/workflows/manual_aw_trigger/workflow.py` — a real BaseWorkflow with 5 operations (init_job, process_batch, record_batch_failure, finalize, handle_error), per-environment config, and a parallel batch processing state machine.
