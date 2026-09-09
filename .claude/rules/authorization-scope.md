# Authorization Scope Binding

## WHY
The authorised scope of an operation (which account / tenant / template the caller may touch) must be derived from something the caller cannot forge. When a resolver or interactor accepts an entity id and then authorizes against a caller-supplied or context-supplied scope instead of the entity's OWN persisted scope, any authenticated user can reach another tenant's data by guessing the id — a cross-tenant IDOR. This is the highest-severity recurring class in this codebase (the request-id variant shipped three times on ADR-021 before security review caught it).

## The Rule
- **Authorize against the resource's own persisted scope.** For any operation keyed by an entity id (`request_id`, `application_id`, etc.), fetch the entity FIRST, then validate access against the scope stored ON that entity — e.g. `validate_officer_management_access(user_id, request.account_id)`. The fetched `request.account_id` is the source of truth.
- **Never authorize against caller-supplied scope.** Do not trust an `account_id` passed as a mutation/query param, `info.context.account_id`, or a `"placeholder_*"` literal to decide what the caller may access. A `_validate_user_access` method left as a `# TODO`/placeholder is an open IDOR — treat it as blocking, not deferred.
- **Fail safe when scope is unresolvable.** If the entity's scope resolves to `None` (not found), reject — never fall back to a caller-supplied value.
- **Do not mask the failure.** Map specific domain exceptions to typed error/union members; never `except Exception: return AccessDenied`, which hides real errors behind an authz label.

## Sibling: write-path scope binding (configio)
The same principle governs configio/populate WRITES: bind the write to the import context's scope, never to a `*_id` column read from a CSV row. That path has its own detailed guards and required test — see the Tenancy section in `configio-architecture.md`. This rule is the general statement; that section is the write-path instance.

## Required test
For any request-id-scoped resolver/interactor, add a test where a caller from account A targets an entity persisted under account B and assert the access validator rejects it BEFORE any read/mutate side effect runs (`assert_not_called()` on the downstream storage/service call). Canonical example: `bps/tests/interactors/test_retry_officer_management_request_interactor.py`.
