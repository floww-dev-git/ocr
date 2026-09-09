---
globs:
  - "**/interactors/**"
---

# Interactor Rules

## Inviolable
- **No Django imports** — no models, ORM queries, or framework objects
- **No HTTP request/response handling** — framework-independent
- **DTO-only I/O** — receives and returns DTOs exclusively

## Constructor Pattern
```python
class CreateEntityInteractor(IamMixin):
    def __init__(
        self,
        storage: EntityStorageInterface,
        related_storage: RelatedStorageInterface,
    ):
        self.storage = storage
        self.related_storage = related_storage

    @property
    def some_service(self) -> SomeService:
        return get_service_adapter().some_service
```
- Type-hint against **abstract interfaces**, never concrete implementations
- Services via `@property` with `get_service_adapter()` — lazy-loaded

## Method Structure
Public method orchestrates: **validate → transform → persist → return DTO**
```python
def create_entity(self, user_id: str, input_dto: CreateEntityDTO) -> EntityDTO:
    self.validate_user_is_admin(user_id=user_id)  # IamMixin
    entity_dto = self._build_entity_dto(input_dto)
    self.storage.create_entity(entity_dto=entity_dto)
    return entity_dto
```
- **One public method per interactor** — the use case entry point
- **The main method reads like a series of steps** — each line should describe one business action. If a reader can't understand the flow by reading just the main method (without looking at private methods), the abstraction level is wrong. Extract multi-line logic into descriptively named private methods so the main method tells a story
- Early exit when no work needed

## Cross-Cutting Mixins
- `IamMixin` — permission checks via `self.iam_service` property
  - `validate_user_is_admin(user_id)`, `validate_pipeline_permission_to_user(user_id, pipeline_id)`
- `ValidationMixin` — entity validation with `@staticmethod` methods
  - Raises domain exceptions on invalid input
- Multi-mixin: `class MyInteractor(IamMixin, ValidationMixin):`

## External Services
- Access **only** via `get_service_adapter()` — never call external APIs directly
- Use `@property` with deferred imports to avoid circular dependencies
