---
globs:
  - "**/*.py"
---

# Exception Handling

## Core rules
- **Never bare `except:`** — it eats `KeyboardInterrupt`/`SystemExit`. *(hook-enforced)*
- **Catch the specific exception**, and wrap only the line that can fail — never a fat block.
- **When you translate, chain** — `raise DomainError(...) from exc` keeps the root cause.
- **`except Exception` only at the outermost boundary** (event handler, job runner, adapter top, resolver) — there it must log + convert, never silently `pass`.
- **Re-raise with bare `raise`**, never `raise exc` — bare keeps the traceback.
- **No try/except "just in case"** — speculative handling hides real bugs.

## Domain exceptions carry context
```python
class EntityNotFoundException(BaseExceptionClass):
    def __init__(self, entity_id: str):
        self.entity_id = entity_id
```

## Translate at the boundary (storage → domain)
```python
try:
    obj = MyModel.objects.get(id=entity_id)
except MyModel.DoesNotExist as exc:
    raise EntityNotFoundException(entity_id=entity_id) from exc
```

## Broad catch — ONLY at the top-level boundary
```python
# one bad event must not kill the worker → log, then convert
def handle_event(self, event):
    try:
        self._process(event)
    except Exception as exc:
        logger.exception("event processing failed")
        raise EventProcessingFailed(event_id=event.id) from exc
```

## Adapter / delegation call — handle, return a failure result
```python
def execute(self, context: ExecutionContext) -> NodeResult:
    try:
        result = self.service_adapter.perform_action(params)
    except SpecificServiceError as exc:
        return NodeResult(status=NodeResultStatus.FAILURE, error=str(exc))
```
Check `None` on service/storage returns before using them.
