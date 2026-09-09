# Query Patterns Reference

## Complete Query Definition Example (from applications/queries.py)

```python
import graphene

from graphql_service.custom_scalars import GQLDateScalar, GQLRequiredList


class GetApplicationFieldsParams(graphene.InputObjectType):
    application_id = graphene.String(required=True)
    field_ids = GQLRequiredList(graphene.String)


class GetApplicationsParams(graphene.InputObjectType):
    pipeline_id = graphene.String(required=True)
    stage_ids = GQLRequiredList(graphene.String)
    offset = graphene.Int(required=True)
    limit = graphene.Int(required=True)
    search_query = graphene.String()
    sort_field_id = graphene.String()
    sort_order = graphene.String()


# In the Queries class:
class Queries:
    get_application_fields = graphene.Field(
        GetApplicationFieldsResponse,
        params=GetApplicationFieldsParams(required=True),
        resolver=resolve_get_application_fields,
    )

    get_applications = graphene.Field(
        GetApplicationsResponse,
        params=GetApplicationsParams(required=True),
        resolver=resolve_get_applications,
    )
```

## Resolver Pattern

```python
# In resolvers/get_entity.py

def resolve_get_entity(root, info, params):
    """
    All imports MUST be lazy — inside the function body.
    This prevents circular imports and keeps the GraphQL layer lightweight.
    """
    from <app>.interactors.<domain>.get_entity import (
        GetEntityInteractor,
    )
    from <app>.storages.<domain>_storage import <StorageClass>
    from sales_crm_graphql.<feature>.types.error_types import (
        EntityNotFound,
        PermissionDenied,
    )

    user_id = info.context.user_id
    storage = <StorageClass>()

    try:
        interactor = GetEntityInteractor(<domain>_storage=storage)
        result = interactor.get_entity(
            user_id=user_id,
            entity_id=params.entity_id,
        )
    except EntityNotFoundException as e:
        return EntityNotFound(message=str(e))
    except UserPermissionDeniedError as e:
        return PermissionDenied(message=str(e))

    return EntityResult(
        entity_id=result.entity_id,
        name=result.name,
    )
```

## Paginated Query Pattern

```python
class GetEntitiesParams(graphene.InputObjectType):
    offset = graphene.Int(required=True)
    limit = graphene.Int(required=True)
    search_query = graphene.String()
    pipeline_id = graphene.String(required=True)


class EntityItem(graphene.ObjectType):
    entity_id = graphene.String(required=True)
    name = graphene.String(required=True)


class GetEntitiesResult(graphene.ObjectType):
    entities = graphene.List(graphene.NonNull(EntityItem))
    total_count = graphene.Int(required=True)


class GetEntitiesResponse(graphene.Union):
    class Meta:
        types = (
            GetEntitiesResult,
            PermissionDenied,
        )
```

## Query Field Registration Options

### Option 1: Direct resolver reference
```python
class Queries:
    get_entity = graphene.Field(
        GetEntityResponse,
        params=GetEntityParams(required=True),
        resolver=resolve_get_entity,
    )
```

### Option 2: List query
```python
class Queries:
    get_entities = graphene.List(
        graphene.NonNull(EntityType),
        params=GetEntitiesParams(required=True),
        resolver=resolve_get_entities,
    )
```

## GraphQL Custom Scalars

```python
from graphql_service.custom_scalars import (
    GQLRequiredList,      # graphene.List(graphene.NonNull(type))
    GQLDateScalar,        # Date scalar (YYYY-MM-DD)
    GQLDateTimeScalar,    # DateTime scalar — NEVER use graphene.DateTime()
)
```

## Error Type Definitions

```python
# In types/error_types.py
import graphene


class EntityNotFound(graphene.ObjectType):
    message = graphene.String(required=True)
    entity_id = graphene.String()


class PermissionDenied(graphene.ObjectType):
    message = graphene.String(required=True)
```

## Common Error Types (from sales_crm_graphql/common_error_types.py)

```python
# Spread in Union for field-response-related operations:
from sales_crm_graphql.common_error_types import (
    COMMON_FIELD_RESPONSE_ERROR_TYPES,
)

class SomeResponse(graphene.Union):
    class Meta:
        types = (
            SomeResult,
            *COMMON_FIELD_RESPONSE_ERROR_TYPES,
            # ... feature-specific errors
        )
```

## DataLoader Integration in Result Types

```python
class EntityResult(graphene.ObjectType):
    entity_id = graphene.String(required=True)
    related_name = graphene.String()

    @staticmethod
    def resolve_related_name(root, info):
        from sales_crm_graphql.<feature>.dataloaders.get_related_name import (
            RelatedNameDataLoader,
        )

        return RelatedNameDataLoader(context=info.context).load(
            key=root.entity_id
        )
```
