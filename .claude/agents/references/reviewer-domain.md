# Reviewer Domain Knowledge — stack-specific anti-patterns & business context

Loaded by the reviewer persona. Framing is review-angled: what each technology makes easy to get wrong.

## Tech Stack Awareness (for catching stack-specific anti-patterns)
- **Django 4.2.16** — missing `select_related`/`prefetch_related` (N+1), queryset evaluation in loops, migration safety, model field choices
- **Graphene 3.2.1** — unbounded queries without pagination, missing permission checks on resolvers, overfetching in nested connections
- **Elasticsearch 7.8.1** — unbounded search queries, missing index refresh in tests, stale index mappings
- **PynamoDB 5.5.1** — scan vs query (cost), missing GSI usage, batch size limits
- **django-cacheops** — cache invalidation gaps, caching mutable objects, stale cache after migrations
- **Serverless (Lambda/Step Functions)** — cold start impact, timeout handling, idempotency, payload size limits, error state handling in Step Functions

## Cloud & Infrastructure
- **AWS S3** — public bucket exposure, missing presigned URL expiry, large file handling
- **AWS Lambda** — function timeout vs API Gateway timeout mismatch, memory configuration, retry behavior
- **AWS Step Functions** — missing error catchers, infinite loops in state machines, execution history limits
- **AWS EventBridge** — event pattern specificity, dead-letter config, cross-account event rules
- **Redis** — cache key collisions, unbounded cache growth, serialization issues

## CRM Domain (for catching business logic errors)
- **Core flow:** Pipeline → Pipeline Items (Deals) → Contacts/Organizations → Activities → Products
- **Government flows:** BPS/TDR — strict status machines, certificate lifecycle, multi-bank operations, regulatory compliance
- **Payments:** Razorpay — amount verification, idempotency, webhook signature validation, refund authorization
- **Cross-cutting:** Permission model (IAM), multi-tenancy (organization scoping), soft deletes, audit trails
