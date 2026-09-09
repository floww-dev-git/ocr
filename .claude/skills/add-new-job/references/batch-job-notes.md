# BatchJob & ImportJob Notes

## BatchJob

When your job processes N records in chunks, extend `BatchJob` instead of `BaseJob`.

**Do NOT override `execute()`** — the platform owns it. Instead implement three methods:

```python
from jobs_engine.base.batch_job import BatchJob
from jobs_engine.registry.job_registry import register_job

@register_job
class YourBatchJob(BatchJob):
    job_type = "<app>.<action>"
    # noinspection PyTypeChecker
    backend_type = BackendType.QUEUE.value
    category = JobCategory.DATA_LOADING.value
    # noinspection PyTypeChecker
    queue_priority = QueuePriority.STANDARD.value
    chunk_size = 100  # records per chunk (default 100)

    def get_total_count(self, context: JobContext) -> int:
        """Return total number of records to process."""
        # Typically a storage count query
        ...

    def get_chunk(self, context: JobContext, offset: int, size: int) -> List[Any]:
        """Return a slice of records. Platform calls this repeatedly."""
        # Typically a storage query with offset + limit
        ...

    def process_record(self, context: JobContext, record: Any) -> None:
        """Process one record. Raise on failure — platform catches per-record."""
        # Delegate to interactor
        ...

    def on_record_complete(self, context: JobContext, record: Any, status: str, error_message: str) -> None:
        """Optional callback after each record. Default is no-op."""
        ...
```

Platform behavior:
- Calls `get_total_count` once, then loops `get_chunk` + `process_record` per record
- Per-record exceptions are caught — one bad record does not abort the batch
- Each record result is stored in `BatchRecord` model (SUCCESS/FAILED)
- Final status: SUCCESS (all passed), PARTIAL (some failed), FAILED (all failed)
- Progress is reported automatically via `report_progress`

## ImportJob

For CSV/file imports backed by `ImportRecord`, extend `ImportJob`. It pre-implements `get_total_count`, `get_chunk`, and `on_record_complete` using `ImportRecordStorage`.

```python
from jobs_engine.base.import_job import ImportJob
from jobs_engine.registry.job_registry import register_job

@register_job
class YourImportJob(ImportJob):
    job_type = "<app>.<action>"

    def process_record(self, context: JobContext, record: ImportRecordDTO) -> None:
        """Process one import record. Platform handles iteration and status updates."""
        row_data = json.loads(record.data)
        # Delegate to interactor
        ...
```

Caller must pre-populate `ImportRecord` rows via `JobServiceInterface.create_import_records()` before publishing the job.

The payload must include `import_id` — `ImportJob` uses it to query pending records.

## Testing BatchJob / ImportJob

Same structure as BaseJob tests, but:
- Test `validate_payload`, `get_total_count`, `get_chunk`, and `process_record` individually
- Do NOT test `execute()` — it raises `NotImplementedError` (platform-owned)
- Mock the storage that `get_total_count` and `get_chunk` query
- For `ImportJob`, patch `jobs_engine.storages.import_record_storage.ImportRecordStorage`
