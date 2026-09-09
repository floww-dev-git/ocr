# Domain Knowledge Reference

Shared domain knowledge for developer and architect agents.

## Migration Safety Checklist

Before every `makemigrations`:
- New columns: has a `default` or `null=True`? If not, existing rows will fail
- Removing columns: is the column still referenced anywhere? Remove code first, column in next deploy
- Adding indexes: use `CREATE INDEX CONCURRENTLY` for large tables (add `atomic = False` to migration)
- Data migrations: batch large updates (`iterator()` + `bulk_update`), never full-table in one transaction
- Test: run `makemigrations` -> `migrate` -> `migrate <app> <previous>` (verify reversibility)
- **Two-phase migrations** — for column renames: add new -> backfill -> switch code -> drop old (across multiple deployments)
- **No table locks** — avoid `ALTER TABLE` operations that lock large tables

## Performance Patterns

- **Batch operations** — `bulk_create`/`bulk_update` with batch_size (default 1000) instead of loops
- **Queryset evaluation** — `.exists()` instead of `len(qs) > 0`, `.count()` instead of `len(qs)`, `.only()`/`.defer()` for partial loads
- **Prefetch strategy** — `select_related` for ForeignKey/OneToOne, `prefetch_related` for ManyToMany/reverse FK
- **Connection awareness** — Django auto-closes idle connections; for Lambda, use short `CONN_MAX_AGE`

## Elasticsearch Practices

- **Bulk indexing** — use `bulk()` helper for batch document indexing, never index one-by-one in loops
- **Mapping updates** — new fields are auto-mapped; changing field types requires reindex
- **Zero-downtime reindex** — use index aliases: create new index -> bulk reindex -> swap alias -> delete old

## Serverless Implementation

- **Idempotency** — every Lambda handler must produce the same result if invoked twice with the same event (use idempotency keys or check-before-write)
- **Structured logging** — use JSON-formatted logs in Lambda for CloudWatch Insights queryability
- **Error handling in Step Functions** — use `Catch` and `Retry` at the task level, not just the state machine level
- **Cold start mitigation** — keep Lambda packages small, use layers for heavy deps, provisioned concurrency for latency-sensitive paths
- **Timeouts** — set Lambda timeout < API Gateway timeout (29s); Step Functions: set `TimeoutSeconds` on every task state

## Backward Compatibility

- **DTO evolution** — new fields must have defaults; never remove fields consumed by other apps without coordinating
- **GraphQL** — add `deprecation_reason` to fields before removal; never change field types in place
- **Storage interfaces** — new methods are safe; changing method signatures requires updating all consumers
- **Event schema versioning** — include `version` field in all asynq events; consumers must handle unknown fields gracefully
- **Idempotent event handlers** — same event delivered twice = same outcome

## Caching Strategy

- **cacheops** — for frequently-read, rarely-written Django model queries (automatic invalidation on save/delete)
- **Elasticsearch** — for complex search, full-text, aggregations, read-heavy dashboards (CQRS read model)
- **Redis direct** — for computed values, rate limiting, session data, short-TTL counters (manual invalidation)
- **No cache** — for real-time financial data, permission checks, data that must be strongly consistent
