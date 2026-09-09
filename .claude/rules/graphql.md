---
globs:
  - "**/sales_crm_graphql/**"
  - "**/ext_client_graphql/**"
---

# GraphQL Rules

## Mutation Structure
```python
class DoSomethingParams(graphene.InputObjectType):
    entity_id = graphene.String(required=True)

class DoSomethingResult(graphene.ObjectType):
    entity_id = graphene.String(required=True)

class DoSomethingResponse(graphene.Union):
    class Meta:
        types = (DoSomethingResult, EntityNotFound, UserIsNotAnAdministrator)

class DoSomething(graphene.Mutation):
    class Arguments:
        params = DoSomethingParams(required=True)

    Output = DoSomethingResponse

    @staticmethod
    def mutate(root, info, params):
        from app.interactors.do_something import DoSomethingInteractor
        from app.storages.storage import Storage

        interactor = DoSomethingInteractor(storage=Storage())
        try:
            result_dto = interactor.do_something(
                user_id=info.context.user_id, entity_id=params.entity_id
            )
        except EntityNotFoundException as err:
            return EntityNotFound(entity_id=err.entity_id)
        except UserIsNotAdmin:
            return UserIsNotAnAdministrator()
        else:
            return DoSomethingResult(entity_id=result_dto.entity_id)
```

### Key rules
- `InputObjectType` for params, **Union** for response (success + error types)
- `@staticmethod mutate(root, info, params)` — no business logic in resolvers
- **Lazy imports** inside `mutate()` to avoid circular dependencies
- Each `except` returns a specific error type with context from exception attributes
- `else` block for success response

## Query Structure
```python
# Standalone resolver function (not class method)
def resolve_get_entity(root, info, params):
    from app.interactors.get_entity import GetEntityInteractor
    from app.storages.storage import Storage

    interactor = GetEntityInteractor(storage=Storage())
    result_dto = interactor.get_entity(
        user_id=info.context.user_id, entity_id=params.entity_id
    )
    return EntityType(id=result_dto.id, name=result_dto.name)

class MyQueries(graphene.ObjectType):
    get_entity = graphene.Field(
        GetEntityResponse, params=GetEntityParams(required=True),
        required=True, resolver=resolve_get_entity,
    )
```

### Key rules
- Resolvers are **standalone functions**, referenced via `resolver=` parameter
- Inline resolvers use `@staticmethod` on the query class
- Defensive checks return error types early (no try-except needed for queries)
- Pagination: extract `params.pagination.offset/limit` → `PaginationDTO`

## Error Types
- All implement `GraphQLBaseError` interface
- Include contextual fields matching exception attributes
```python
class EntityNotFound(graphene.ObjectType):
    class Meta:
        interfaces = (GraphQLBaseError,)
    entity_id = graphene.String(required=True)
```

## Custom Scalars
- **Never use `graphene.DateTime()`** — always use `GQLDateTimeScalar` from `graphql_service.custom_scalars`
- Import: `from graphql_service.custom_scalars import GQLDateTimeScalar`
- Nullable: `created_at = GQLDateTimeScalar()` | Required: `created_at = GQLDateTimeScalar(required=True)`

## DataLoaders
- Extend `graphql_service.dataloaders.BaseDataLoader`
- Set `context_key` and `cache = True`
- `async def batch_load(self, keys)` — return results in same order as keys
- Instantiate with `context=info.context`, call `.load(key=)`

## Integration Tests
- Inherit `GraphQLBaseTestCase` from `graphql_service.utils.base_test`
- Use `@pytest.mark.django_db` decorator
- Define `QUERY`/`MUTATION` as class attributes — never inline
- Use `snapshot` fixture for complex response validation
- Test at least one error case and one success case per operation
