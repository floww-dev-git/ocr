# CLAUDE.md

Django CRM backend using Clean Architecture (interactors, storage interfaces, adapters, DTOs). Architecture, clean code, exception handling, testing, and GraphQL rules live in `.claude/rules/` — auto-loaded, don't duplicate here.

## Development Environment

```bash
# Bootstrap
pip install virtualenv && virtualenv venv && source venv/bin/activate
pip install -r requirements_project.txt && pip install -r requirements_test.txt
export DJANGO_SETTINGS_MODULE=sales_crm_backend.settings.local

# Core commands
python manage.py build -a sales_crm_core
python manage.py makemigrations && python manage.py migrate
python manage.py runserver
pytest

# GraphQL schema regeneration (required when sales_crm_graphql/, ext_client_graphql/, floww_cli_graphql/, or citizen_search_graphql/ change)
python manage.py schema_gen --schema sales_crm_graphql.schema.schema
python manage.py schema_gen --schema ext_client_graphql.schema.schema --out ext_client_schema --schema_enum EXT_CLIENT_SCHEMA
python manage.py schema_gen --schema floww_cli_graphql.schema.schema --out floww_cli_schema --schema_enum FLOWW_CLI_SCHEMA
python manage.py schema_gen --schema citizen_search_graphql.schema.schema --out citizen_search_schema --schema_enum CITIZEN_SEARCH_SCHEMA
```

Always activate venv before running commands.

## Key Technologies

Django 4.2.16, Graphene 3.2.1, Elasticsearch 7.8.1, PynamoDB 5.5.1 (DynamoDB), BigQuery, AWS (S3, Lambda, Step Functions, EventBridge), Razorpay, Redis, PostgreSQL.

## Django Apps

| Category | Apps |
|---|---|
| Core | sales_crm_core, iam, asynq |
| Business | bps, automation_workflows, fee_engine, payments_engine |
| Integration | plugins, portals, analytics_copilot |
| API | sales_crm_graphql, ext_client_graphql, floww_cli_graphql |
| Supporting | engine_variables, ib_templates, crm_scoring, scrutiny_report |
| Infrastructure | jobs_engine (tracked, retryable background jobs via SQS + Lambda) |

Each app has its own `CLAUDE.md` with domain context — auto-loaded when you touch files in that app.

## Operational Patterns (pointers, not how-tos)

- **Elasticsearch**: index definitions in `documents/`, utilities in `common/elasticsearch/`, patterns in `crm_elasticsearch/`
- **External integrations**: adapter pattern in `adapters/`, log calls via `external_integration_request_log` model
- **Event processing**: `asynq` app, handlers in `event_handlers/`, config via `PublishEventConfig` model
- **Testing**: pytest + Factory Boy (`tests/factories/`), shared fixtures in `common_fixtures/`

## Skills

Skills self-route: every skill's description (with its trigger phrases) is auto-surfaced to the
model — match the task to a skill and invoke it BEFORE working manually; the skill encodes the
proven workflow. Browse `.claude/skills/` or type `/` for the full catalog.

## Context & Persistence

- Context auto-compacts — don't stop tasks early to save tokens. Finish the job.
- Before compaction or context loss, save progress to `feature-context.md`: current task, completed work, next steps, open questions.
- On resume, read `feature-context.md` and branch state before asking the user what to do.
- Never silently drop context — if you're about to lose track, write it down first.
- Don't stop at the first obstacle. Investigate, retry, then ask.

## Safety

- Local reversible actions (edits, tests) proceed freely. Destructive actions (deleting files/branches, force-push, dropping tables, modifying shared infra) require explicit user confirmation.
- Never bypass safety checks (`--no-verify`, `--force`) to work around obstacles.
- No confirmation bias — back claims with evidence (file contents, test output). Say "I haven't verified this" when you haven't.

## Operational Memory

- Always run commands inside venv.
- Always show test summary after running tests.
- Feature docs live under the owning app, one folder per feature: `<app>/docs/features/<feature-slug>/` — layout + naming in `.claude/rules/references/feature-folder.md`. Standalone one-off ADRs: `<app>/docs/adrs/`.

## graphify

This project has a knowledge graph at graphify-out/ with god nodes, community structure, and cross-file relationships.

Rules:
- For codebase questions, first run `graphify query "<question>"` when graphify-out/graph.json exists. Use `graphify path "<A>" "<B>"` for relationships and `graphify explain "<concept>"` for focused concepts. These return a scoped subgraph, usually much smaller than GRAPH_REPORT.md or raw grep output.
- If graphify-out/wiki/index.md exists, use it for broad navigation instead of raw source browsing.
- Read graphify-out/GRAPH_REPORT.md only for broad architecture review or when query/path/explain do not surface enough context.
- After modifying code, run `graphify update .` to keep the graph current (AST-only, no API cost).
