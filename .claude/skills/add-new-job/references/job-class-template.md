# Job Class Template

Annotated template for a `BaseJob` implementation. Every line has a comment explaining WHY.

```python
import json                                    # JobResult.data must be a JSON string
from typing import Dict

from jobs_engine.base.base_job import BaseJob  # Always import base class at top level
from jobs_engine.constants.enums import JobCategory, JobStatus, QueuePriority
from jobs_engine.dtos.job_dtos import JobContext, JobResult
from jobs_engine.exceptions.custom_exceptions import (
    InvalidJobPayload,                         # Raised in validate_payload
    PermanentFailure,                          # Wraps domain errors that should NOT retry
)
from jobs_engine.registry.job_registry import register_job


@register_job                                  # Adds class to _REGISTRY at import time
class YourJobNameJob(BaseJob):
    # --- Class-level config (read by the platform) ---
    job_type = "<app>.<action>"                # MUST match ^[a-z_]+\.[a-z_]+$
    # noinspection PyTypeChecker
    category = JobCategory.EVENT.value         # Enum .value + noinspection comment
    # noinspection PyTypeChecker
    queue_priority = QueuePriority.STANDARD.value
    max_retries = 3                            # 0 = no retries (immediate fail on error)
    timeout_seconds = 300                      # Lambda kill timeout
    idempotency_fields = ("entity_id",)        # Tuple of payload keys for dedup hash
    idempotency_window_hours = 24              # How long to remember the dedup hash

    @classmethod
    def validate_payload(cls, payload: Dict) -> None:
        """Called before publish. Gate bad data early — saves a queue round-trip."""
        entity_id = payload.get("entity_id")
        if not entity_id or not isinstance(entity_id, str):
            raise InvalidJobPayload(
                job_type=cls.job_type,
                message="entity_id is required and must be a non-empty string",
            )

    def execute(self, context: JobContext) -> JobResult:
        """Called by the platform. Delegate to interactor, map exceptions."""
        # Lazy imports — avoid circular dependencies at module level
        from some_app.interactors.do_something import DoSomethingInteractor
        from some_app.exceptions.custom_exceptions import (
            EntityNotFound,
            InvalidConfiguration,
        )

        # Extract payload
        entity_id = context.payload["entity_id"]

        # Delegate to interactor
        try:
            result_dto = DoSomethingInteractor().do_something(
                entity_id=entity_id,
                tenant_id=context.tenant_id,
            )
        except EntityNotFound as exc:
            # Permanent: retrying won't help if the entity doesn't exist
            raise PermanentFailure(message=f"Entity not found: {exc.entity_id}")
        except InvalidConfiguration as exc:
            # Permanent: bad config won't fix itself on retry
            raise PermanentFailure(message=str(exc))
        # NOTE: Unhandled exceptions trigger default retry with backoff.
        # Only catch exceptions you need to classify as Permanent or Transient.

        return JobResult(
            # noinspection PyTypeChecker
            status=JobStatus.SUCCESS.value,
            message="Describe what succeeded",
            data=json.dumps({"result_id": result_dto.id}),
        )
```

## Exception Mapping Rules

| Exception type | Action | Rationale |
|---|---|---|
| Data doesn't exist | `raise PermanentFailure(...)` | Retrying won't create the data |
| Auth/permission failure | `raise PermanentFailure(...)` | Permissions won't change on retry |
| Invalid input/config | `raise PermanentFailure(...)` | Bad input stays bad |
| External service timeout | `raise TransientFailure(...)` | Service may recover |
| Rate limit / throttle | `raise TransientFailure(...)` | Backoff will help |
| Unknown / unexpected | Don't catch — let it propagate | Platform retries with backoff, then EXHAUSTED |

## Canonical Example

`tdr/jobs/generate_validation_report_job.py` — a real BaseJob that validates S3 URLs, delegates to a report interactor, handles multiple exception types, and returns structured data.

## S3 File Processing Job Example

For jobs that download a CSV from S3, process it, and upload results back to S3. The job class delegates to an interactor that inherits `BaseS3DataLoading`. See `references/s3-file-processing-patterns.md` for the full interactor pattern.

```python
import json
from typing import Dict

from jobs_engine.base.base_job import BaseJob
from jobs_engine.constants.enums import JobCategory, JobStatus, QueuePriority
from jobs_engine.dtos.job_dtos import JobContext, JobResult
from jobs_engine.exceptions.custom_exceptions import (
    InvalidJobPayload,
    PermanentFailure,
)
from jobs_engine.registry.job_registry import register_job


@register_job
class MyS3ProcessingJob(BaseJob):
    job_type = "app_name.process_csv"
    # noinspection PyTypeChecker
    category = JobCategory.DATA_LOADING.value
    # noinspection PyTypeChecker
    queue_priority = QueuePriority.STANDARD.value
    max_retries = 2
    timeout_seconds = 900
    idempotency_fields = ("source_csv_s3_url",)
    idempotency_window_hours = 1

    @classmethod
    def validate_payload(cls, payload: Dict) -> None:
        source_csv_s3_url = payload.get("source_csv_s3_url")
        if not source_csv_s3_url or not isinstance(source_csv_s3_url, str):
            raise InvalidJobPayload(
                job_type=cls.job_type,
                message="source_csv_s3_url is required and must be a non-empty string",
            )

    def execute(self, context: JobContext) -> JobResult:
        # Lazy imports — the interactor inherits BaseS3DataLoading
        from app_name.dataio.my_processor import MyProcessorInteractor
        from app_name.dataio.exceptions import InvalidS3URL, S3FileNotFound

        source_csv_s3_url = context.payload["source_csv_s3_url"]

        try:
            # Interactor handles: download CSV -> process -> upload -> return S3 URL
            s3_url = MyProcessorInteractor().execute(
                source_csv_s3_url=source_csv_s3_url
            )
        except (InvalidS3URL, S3FileNotFound) as exc:
            raise PermanentFailure(message=str(exc))

        return JobResult(
            # noinspection PyTypeChecker
            status=JobStatus.SUCCESS.value,
            message="CSV processing completed",
            data=json.dumps({"s3_url": s3_url}),
        )
```

**Key points:**
- The job class does NOT import S3 utilities — that is the interactor's responsibility
- `execute()` receives an S3 URL in the payload and returns an S3 URL in the result
- The interactor returns a full S3 URL (via `S3Service().get_s3_file_url()`), not a raw key
- Canonical real example: `tdr/jobs/get_application_id_from_file_no_job.py`
