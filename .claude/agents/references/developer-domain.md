# Developer Domain Knowledge

## Frameworks & Libraries
- **Django 4.2.16** — ORM, migrations, management commands, middleware, signals
- **Graphene 3.2.1** — GraphQL schema, mutations (relay), queries, input types, resolvers, connections
- **PynamoDB 5.5.1** — DynamoDB models, indexes, queries, batch operations
- **Elasticsearch DSL 7.8.1** — document definitions, search queries, aggregations, index management
- **django-cacheops** — queryset caching, cache invalidation patterns
- **Factory Boy** — test factories, lazy attributes, SubFactory, RelatedFactory, traits
- **pytest** — fixtures, parametrize, markers, conftest patterns, `--no-migrations`

## Cloud & Serverless
- **AWS S3** — file upload/download, presigned URLs, bucket operations
- **AWS Lambda** — serverless function handlers, event payloads, cold starts, timeouts
- **AWS Step Functions** — state machine definitions, task states, error handling, retry policies
- **AWS EventBridge** — event patterns, rules, scheduled events, cross-service triggers
- **AWS SQS** — message queues, dead-letter queues, visibility timeouts

## Payments & Integrations
- **Razorpay SDK** — order creation, payment capture, webhook verification, refund flows
- **DocuSign** — envelope creation, signing flows, webhook callbacks
- **asynq** — event publishing, event handlers, PublishEventConfig

## CRM Domain
- **Core entities:** Pipelines, Pipeline Items (Deals), Contacts, Organizations, Activities, Products
- **Government:** BPS (Business Process Services), TDR (Transfer of Development Rights) — certificates, multi-bank flows, status machines
- **Modules:** IAM (permissions/roles), Fee Engine (fee calculations), Automation Workflows (triggers/actions), ConfigIO (bulk import/export), CRM Scoring, Scrutiny Reports

## Database Patterns
- PostgreSQL: `select_related`/`prefetch_related`, `select_for_update`, bulk operations, custom managers
- Elasticsearch: CQRS reads, document indexing, nested queries, aggregations
- DynamoDB: single-table design, GSI queries, batch writes
- Redis: cacheops integration, cache key patterns, invalidation strategies

## Best Practices

For migration safety, performance patterns, Elasticsearch practices, serverless implementation, and backward compatibility, see `.claude/agents/references/domain-knowledge.md`.
