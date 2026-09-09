# Gateway types — identifying the operation and driving the door

One namespace per front door lives in `common/tests/common_fixtures/gateways.py` — each calls
the REAL production entry point. This file maps each gateway type to: how to pin the
operation's input/output (workflow Step 1), where discovery starts (Step 2), and how to Act.

## GraphQL (`gql`)

| Aspect | Where |
|---|---|
| Operation | The mutation/query name in the schema (e.g. `getFeeRuleSetLogs`) |
| Input | The params `InputObjectType` on the resolver/mutation |
| Output | The response union — EVERY branch (success + each typed error) |
| Discovery entry | `sales_crm_graphql/<app>/mutations/<op>.py` or `resolvers/<op>.py` → the interactor it instantiates |
| Act | `gql.run(QUERY, variables=..., user_id=...)` |

The shared operation document lives ONCE in the package `__init__.py`, fully expanded — the
whole return type resolved recursively: every union branch via `... on <Type>`, every nested
selection, fragments for repeated shapes. Exemplar:
`fee_engine/tests/gateway_tests/get_fee_rule_set_logs/__init__.py`.

### Sync vs async executor — the load-bearing choice

- **`gql.run` (default).** Drives `execute_schema_v0` — the SYNCHRONOUS executor. Resolvers
  run inline on the test's own DB connection, so rows created inside pytest-django's
  transaction are visible. Use for every case whose selected fields resolve inline.
- **`gql.run_async` (exception).** Drives `execute_schema` — the ASYNC executor that runs the
  DataLoaders (batched relational reads). Its worker resolves on a DIFFERENT DB connection
  that only sees COMMITTED rows — so the test MUST use
  `@pytest.mark.django_db(transaction=True)` (real commits), not the default
  transaction-wrapped mark. Reach for it ONLY when the assertion needs dataloader-backed
  fields fully resolved (grouped views, totals, batched child lists); it is slower and the
  committed-rows requirement is easy to trip.
- `gql.run_or_raise` unwraps the first error's original exception — handy for asserting a
  raised domain exception rather than a union error branch.

## SQS jobs (`sqs`)

| Aspect | Where |
|---|---|
| Operation | The job type / handler registered with jobs_engine |
| Input | The message body dict the producer enqueues |
| Output | Side effects only (store writes, follow-on events) — no response object |
| Discovery entry | `jobs_engine/lambda_handlers/sqs_handler.py` → the job registry → the job's `execute` |
| Act | `sqs.deliver([message_dict])` — builds the real `Records` event and drives the real Lambda handler |

You never test transport delivery; you build the exact message the producer would send and
drive the real handler. Assert = stores snapshot (+ any job-tracking rows jobs_engine writes).

## Async events (`async_event`)

| Aspect | Where |
|---|---|
| Operation | The asynq event type + its registered handler(s) |
| Input | The record dicts the publisher emits |
| Output | Side effects only |
| Discovery entry | `worker_handler.lambda_handler` → asynq routing (`PublishEventConfig`) → the app's `event_handlers/` |
| Act | `async_event.deliver([record_dict])` — the real top-level worker Lambda entry |

## Scheduler ticks (`scheduler`)

| Aspect | Where |
|---|---|
| Operation | What one tick dispatches (due scheduled jobs) |
| Input | Time — arrange due/not-due rows and freeze the clock accordingly |
| Output | Tick return dict + side effects of dispatched jobs |
| Discovery entry | `jobs_engine/lambda_handlers/scheduler_handler.py` |
| Act | `scheduler.tick()` (one real tick) or `scheduler.deliver_eventbridge()` (the EventBridge wrapper) |

The clock IS the input: `@freeze_time` picks which arranged schedules are due.

## Step functions (`step_function`)

| Aspect | Where |
|---|---|
| Operation | The step/operation name in the state-machine event |
| Input | The event dict a state passes to the Lambda |
| Output | The handler's return dict (feeds the next state) + side effects |
| Discovery entry | `jobs_engine/lambda_handlers/step_function_handler.py` (jobs_engine workflows) or `service_handlers/step_function_handler.py` (domain handlers) |
| Act | `step_function.dispatch(event)` / `step_function.dispatch_domain(event)` |

Assert BOTH the return dict (the next state's input — it is contract) and the stores.

## Common to every type

- **Stores:** the package conftest imports `wire_stores` (autouse moto DynamoDB + fakeredis)
  plus the named fixtures — copy `fee_engine/tests/gateway_tests/conftest.py`. Relational is
  sqlite3 via `@pytest.mark.django_db`; a flow depending on Postgres-only semantics
  (JSONField ops, `select_for_update`) runs under the `local_tests` settings instead.
- **Externals:** stub at the wire only — `stub_razorpay` / `stub_docusign` /
  `stub_aws_transport` from `externals.py`. Stubbing your own adapter is a mock of the
  system under test and defeats the front-door premise.
- **Cross-app home (README rule 3):** the operation's test package lives in the app where
  the resolver's/handler's INTERACTOR lands, not necessarily where the schema/handler file
  sits — and its row goes in THAT app's `index.md`.
- **`index.md` compass:** every app's `gateway_tests/` opens with one; the gateway TYPE is a
  column there (never in the package folder name); update it in the same change as a test.
