# S3 File Processing Patterns

Patterns for jobs that download a CSV from S3, process it, and upload results back to S3.

## CSV Download from S3 URL

Convert an S3 URL (e.g., `https://bucket.s3.amazonaws.com/path/file.csv`) to an S3 key, then read CSV rows into memory:

```python
from common.aws_s3.s3_mixin import S3Mixin
from common.utils.get_csv_data_from_s3_key import get_csv_data_from_s3_key

# Step 1: Extract relative S3 key from full URL
input_s3_key = S3Mixin.get_object_relative_path_to_s3_bucket(file_url=source_csv_s3_url)

# Step 2: Download and parse CSV into List[Dict[str, str]]
rows = get_csv_data_from_s3_key(s3_key=input_s3_key)
```

- `S3Mixin.get_object_relative_path_to_s3_bucket()` is a `@staticmethod` -- call on the class, not an instance.
- `get_csv_data_from_s3_key()` returns `List[Dict]` -- each dict is one CSV row keyed by column header.

## CSV Upload to S3

Use `S3Service.put_object()` to upload in-memory content (e.g., CSV built via `csv.DictWriter` + `io.StringIO`):

```python
from common.aws_s3.s3_service import S3Service

S3_EXPORT_PATH = "app_name/export-folder"

def _upload_to_s3(self, csv_content: str, account_id: str) -> str:
    import os
    from datetime import datetime, timezone

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    file_name = f"export_{account_id}_{timestamp}.csv"
    s3_key = os.path.join(S3_EXPORT_PATH, file_name)
    s3_service = S3Service()
    url = s3_service.put_object(body=csv_content, file_name=s3_key)
    return url
```

- `put_object()` uploads and returns a full S3 URL via `get_s3_file_url()`.
- The returned URL uses virtual-hosted-style format (`https://{bucket}.s3.amazonaws.com/{key}`), which is compatible with `get_key_from_s3_url()` for presigned URL generation.

## Return Value: S3 URL (not key, not signed URL)

`S3Service().put_object()` already returns a full S3 URL -- use it directly as the return value.
The job's `JobResult.data` includes this URL: `json.dumps({"s3_url": s3_url})`

**Do NOT:**
- Return the raw `s3_key` -- callers expect a full URL
- Use `generate_presigned_url()` or signed URLs -- they expire
- Invent a custom URL builder -- always use `S3Service().put_object()` return value or `S3Service().get_s3_file_url()`

## Complete S3-to-S3 Processing Pattern

```python
import csv
import io
import os
from datetime import datetime, timezone
from typing import Dict, List, Optional

from common.aws_s3.s3_mixin import S3Mixin
from common.aws_s3.s3_service import S3Service
from common.utils.get_csv_data_from_s3_key import get_csv_data_from_s3_key

S3_OUTPUT_PATH = "app_name/output-folder"
CSV_COLUMNS = ["col_a", "col_b", "col_c"]


class MyS3ProcessingInteractor:
    def execute(self, source_csv_s3_url: str, account_id: str) -> Optional[str]:
        # 1. Download
        input_s3_key = S3Mixin.get_object_relative_path_to_s3_bucket(
            file_url=source_csv_s3_url
        )
        rows = get_csv_data_from_s3_key(s3_key=input_s3_key)

        # 2. Process (in memory -- no temp files)
        output_rows = self._process_rows(rows=rows)
        if not output_rows:
            return None

        # 3. Build CSV in memory
        csv_content = self._build_csv_content(rows=output_rows)

        # 4. Upload and return URL
        return self._upload_to_s3(
            csv_content=csv_content, account_id=account_id
        )

    @staticmethod
    def _build_csv_content(rows: List[Dict[str, str]]) -> str:
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
        return output.getvalue()

    @staticmethod
    def _upload_to_s3(csv_content: str, account_id: str) -> str:
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        file_name = f"export_{account_id}_{timestamp}.csv"
        s3_key = os.path.join(S3_OUTPUT_PATH, file_name)
        s3_service = S3Service()
        return s3_service.put_object(body=csv_content, file_name=s3_key)

    def _process_rows(self, rows: List[Dict[str, str]]) -> List[Dict[str, str]]:
        # Per-row processing logic here
        ...
```

## In-Memory Processing Mandate

All CSV processing happens in memory. Do NOT:
- Write to temp files (`tempfile`, `NamedTemporaryFile`, etc.)
- Write to disk then upload
- Use `open()` for intermediate files

The `get_csv_data_from_s3_key()` utility already handles streaming S3 bytes into `io.StringIO` internally.

## Reference Files

| Utility | Import path | Type |
|---------|-------------|------|
| `S3Mixin` | `common.aws_s3.s3_mixin` | URL-to-key extraction (`@staticmethod`) |
| `get_csv_data_from_s3_key` | `common.utils.get_csv_data_from_s3_key` | CSV download + parse |
| `S3Service` | `common.aws_s3.s3_service` | S3 operations: `put_object()`, `get_s3_file_url()`, `generate_signed_url()` |

## Canonical Examples

- **Interactor**: `tdr/dataio/bulk_file_no_lookup.py` (`BulkFileNoLookupInteractor`) -- full download-process-upload cycle
- **Job class**: `tdr/jobs/get_application_id_from_file_no_job.py` -- delegates to the interactor, maps exceptions to `PermanentFailure`

## Do NOT

- Write custom S3 download/upload helpers -- use the utilities above
- Call `S3Mixin` as an instance for `get_object_relative_path_to_s3_bucket` -- it is a `@staticmethod`
- Return `s3_key` from the interactor when the caller expects a URL
- Use `generate_presigned_url()` for output file URLs
- **Use `common.services.s3_service.S3Service`** (the OLD service) -- it returns path-style URLs (`https://s3-{region}.amazonaws.com/{bucket}/{key}`) which break presigned URL generation. The `get_key_from_s3_url()` utility extracts the URL path as the S3 key, so path-style URLs cause the bucket name to be included in the key, resulting in `NoSuchKey` errors. **Always use `common.aws_s3.s3_service.S3Service`** (virtual-hosted-style: `https://{bucket}.s3.amazonaws.com/{key}`).
