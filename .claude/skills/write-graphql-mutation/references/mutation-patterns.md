# Mutation Patterns Reference

## Complete Mutation Example (from create_application.py)

```python
import graphene

from graphql_service.custom_scalars import GQLRequiredList
from sales_crm_graphql.common_error_types import (
    COMMON_FIELD_RESPONSE_ERROR_TYPES,
)
from sales_crm_graphql.common_types import FieldResponseParams


class CreateApplicationParams(graphene.InputObjectType):
    pipeline_id = graphene.String()
    pipeline_item_template_id = graphene.String()
    record_creation_config_id = graphene.Int(required=True)
    field_responses = GQLRequiredList(FieldResponseParams)
    assignee_field_ids_to_notify = GQLRequiredList(graphene.String)


class CreateApplicationResult(graphene.ObjectType):
    application_id = graphene.String(required=True)
    pipeline_id = graphene.String(required=True)
    application_template_id = graphene.String(required=True)
    has_permission = graphene.Boolean(required=True)

    @staticmethod
    def resolve_pipeline_id(root, info):
        if root.pipeline_id:
            return root.pipeline_id
        from sales_crm_graphql.configuration.leads.dataloaders.get_pipeline_item_template_pipeline import (
            GetPipelineItemTemplatePipelineLoader,
        )

        loader = GetPipelineItemTemplatePipelineLoader(context=info.context)
        return loader.load(key=root.application_template_id)

    @staticmethod
    def resolve_has_permission(root, info):
        from sales_crm_graphql.pipeline_item.dataloaders.get_pipeline_item_permission_status import (
            PipelineItemPermissionStatusDataLoader,
        )

        return PipelineItemPermissionStatusDataLoader(
            context=info.context
        ).load(key=root.application_id)


class CreateApplicationResponse(graphene.Union):
    class Meta:
        types = (
            CreateApplicationResult,
            *COMMON_FIELD_RESPONSE_ERROR_TYPES,
            application_error_types.UserDoesNotHaveAccessToCreateApplication,
            RecordCreationConfigNotFound,
            RecordCreationConfigAccessDenied,
            pipeline_err_types.PipelineNotFound,
            pipeline_err_types.PipelineAccessDenied,
            application_error_types.NotApplicationPipeline,
            error_types.DuplicateFieldIds,
            error_types.FieldsNotFound,
            # ... all possible error types
        )


class CreateApplication(graphene.Mutation):
    class Arguments:
        params = CreateApplicationParams(required=True)

    Output = CreateApplicationResponse

    @staticmethod
    def mutate(root, info, params):
        # All imports lazy — inside method body
        from sales_crm_core.interactors.applications.create_application import (
            CreateApplicationInteractor,
        )
        from sales_crm_core.storages.application_storage import (
            ApplicationStorage,
        )

        user_id = info.context.user_id
        storage = ApplicationStorage()

        try:
            interactor = CreateApplicationInteractor(
                application_storage=storage
            )
            result = interactor.create_application(
                user_id=user_id,
                params=params,
            )
        except application_exceptions.UserDoesNotHaveAccessToCreateApplication:
            return application_error_types.UserDoesNotHaveAccessToCreateApplication(
                message="User does not have access"
            )
        # ... handle all other exceptions

        return CreateApplicationResult(
            application_id=result.application_id,
            pipeline_id=result.pipeline_id,
            application_template_id=result.application_template_id,
        )
```

## Three-Class Pattern Summary

### 1. Params (InputObjectType)
- Defines what the caller sends
- Use `graphene.String(required=True)` for required fields
- Use `GQLRequiredList(graphene.String)` for required lists
- Use `graphene.String()` (no required) for optional params

### 2. Result (ObjectType)
- Defines the success response shape
- Use `@staticmethod` resolvers for computed fields
- Use DataLoaders inside resolvers for efficiency
- Lazy imports in resolver bodies

### 3. Response (Union)
- Union of Result + all error types
- Always include `*COMMON_FIELD_RESPONSE_ERROR_TYPES` if field responses involved
- Include every domain-specific error type the interactor can raise

## Error Type Pattern

```python
# In types/error_types.py
import graphene


class EntityNotFound(graphene.ObjectType):
    message = graphene.String(required=True)
    entity_id = graphene.String()  # Optional: include relevant context


class PermissionDenied(graphene.ObjectType):
    message = graphene.String(required=True)


class DuplicateEntityName(graphene.ObjectType):
    message = graphene.String(required=True)
    name = graphene.String()
```

## Common Scalars

```python
from graphql_service.custom_scalars import (
    GQLRequiredList,      # Non-nullable list
    GQLDateScalar,        # Date scalar (YYYY-MM-DD)
    GQLDateTimeScalar,    # DateTime scalar — NEVER use graphene.DateTime()
)
```

## Schema Registration

```python
# In sales_crm_graphql/<feature>/schema.py
from sales_crm_graphql.<feature>.mutations.<mutation_module> import (
    <MutationClass>,
)


class Mutations:
    <snake_case_name> = <MutationClass>.Field()
```

## Context Access

```python
# Get authenticated user ID
user_id = info.context.user_id

# Get request object
request = info.context

# Get account ID (via IAM)
from iam.app_interfaces.iam_interface import IamInterface
account_id = IamInterface().get_pipeline_account_id(user_id=user_id)
```
