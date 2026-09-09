<!-- GENERATED FILE — DO NOT EDIT BY HAND. -->
<!-- Regenerate: python3 .claude/scripts/generate-module-map.py — source of truth is each app's own CLAUDE.md. -->

# Module Map

One-glance index of every app/module capability. Feeds the intake flow's "cheap scan" (requirement-phase station 1, beat 1) so the manager can propose candidate modules WITHOUT reading every CLAUDE.md.

This is a GENERATED VIEW of the app CLAUDE.mds — the single source of truth stays in each app. Hand-editing this file is drift; regenerate instead:

```bash
python3 .claude/scripts/generate-module-map.py
```

_Generated 2026-07-03. App granularity only — the cheap scan proposes candidate APPS; sub-module detail lives in each app's own CLAUDE.md (read at beat 3) and in Phase 2's impact map. Full view: `--with-submodules`._

## Core

| module | capability |
|---|---|
| `asynq` | Asynchronous event processing via AWS SQS. Routes domain events from producers to handlers registered by consumer apps. Owns no business lo… |
| `iam` | Identity, access control, and organizational structure for the multi-tenant CRM. Every other app depends on IAM for auth checks, user looku… |
| `sales_crm_core` | Central CRM platform: contacts, pipelines, pipeline items (leads/deals/applications), fields, tasks, lead distribution, activities, and cus… |

## Business

| module | capability |
|---|---|
| `automation_workflows` | Event-driven and scheduled workflow automation for pipeline items. Triggers on CRM events or cron schedules, executes node trees (actions,… |
| `bps` | Business Process System: application processing, TDR requests, site inspections, and verification workflows attached to pipeline items. Doe… |
| `fee_engine` | Fee configuration, formula-based calculation, and payment order management for CRM entities. Does NOT collect payments (payments_engine), r… |
| `payments_engine` | Manages end-to-end payment lifecycle: order creation, Razorpay payment processing, refunds, bank reconciliation, and TDR handling. Acts as… |

## Integration

| module | capability |
|---|---|
| `analytics_copilot` | AI-powered natural language analytics for CRM pipelines. Users ask questions in plain text, the external copilot service generates data res… |
| `plugins` | Third-party integration orchestration: document generation (DMS), WhatsApp messaging, cloud calling, and digital signing. Multi-tenant — ea… |
| `portals` | Manages citizen-facing portals for government/organizational services. Portals expose pipeline-backed application workflows to external use… |

## API

| module | capability |
|---|---|
| `floww_cli_graphql` | GraphQL schema package consumed by the floww_cli terminal tool — a Go-based, AI-powered CLI that communicates with crm-backend. Like ext_cl… |
| `sales_crm_graphql` | Primary GraphQL API gateway. Wires schema to interactors in business apps. Contains NO business logic — schemas, resolvers, error types, wi… |

## Supporting

| module | capability |
|---|---|
| `crm_scoring` | Configurable entity scoring engine. Scores CRM entities (leads, applications) based on weighted parameters with conditional rules. Evaluate… |
| `engine_variables` | Dynamic variable computation engine for construction/real estate applications. Defines configurable variables (formulas, conditions, slabs,… |
| `ib_templates` | Dynamic form template engine. Defines form structure (templates, fields, groups, rules, workflows) and stores form data (records, field res… |
| `scrutiny_report` | Manages building plan scrutiny: submitting CAD/drawing files to external scrutiny services, tracking multi-stage progress, syncing results… |

## Infrastructure

| module | capability |
|---|---|
| `jobs_engine` | Unified Job Execution Platform. Tracked, retryable, observable background jobs backed by SQS + Lambda + Step Functions. Does NOT own job bu… |

## Other

| module | capability |
|---|---|
| `bps_integrations` | REST API gateway for external government department integrations with the BPS (Building Permission System). Receives inbound API calls from… |
| `common` | Shared utilities and infrastructure consumed by all apps. No business logic lives here. |
| `functions` | Dynamic Python code execution engine. Stores user-defined functions (Python code as text) per account and executes them at runtime via exec… |
| `graphql_service` | Shared GraphQL infrastructure for sales_crm_graphql and ext_client_graphql. Custom scalars, context, dataloader base, error interface, test… |
| `ib_collections` | Data organization and filtering system: hierarchical collections with tree traversal, multi-condition filter engine, and per-user customiza… |
| `ib_payments` | Multi-gateway payment processing with rule-based fee calculation. Handles payment lifecycle from creation through gateway processing (Razor… |
| `layouts` | Skeleton app -- no active models or interactors. All layout functionality lives elsewhere: |
| `licenses` | Owns the full LTP (Licensed Technical Professional) licence domain. |
| `rules_engine` | Configuration-driven rule evaluation engine. Evaluates RuleSets against entity field data to produce actions (show/hide fields, validate, a… |
| `tdr` | Government-issued development rights certificates as a non-monetary payment instrument. Owns certificate accounts, transactions, utilizatio… |

## No capability card yet

Local apps registered in INSTALLED_APPS (from `sales_crm_backend/settings/base_swagger_utils.py`) with no CLAUDE.md — AI-readiness debt:

- `geo_gov_engine`
- `workflow_engine`

