---
name: design-db
description: Project a database schema from the blueprint's locked entity model — tables, indexes, constraints, and migration shape as a projection of entities the model already settled, never a fresh derivation. Feeds the ADR's Entities & Data Design section. Use when the user says "design database", "create schema", "model the tables", "design DB for feature", or needs a schema projected from a locked domain model.
argument-hint: "[use case or feature description]"
disable-model-invocation: false
allowed-tools: Read, Grep, Glob, Write
---

# Design Database

Project the schema for: $ARGUMENTS

Follow @.claude/rules/models.md and @.claude/rules/clean-architecture.md

This skill runs at pipeline position B2b — AFTER the blueprint's "model locked ✓". The schema is a
**projection** of those locked entities, never a fresh derivation. Do not re-ask what the model
already settled (relationships, entity shapes, ownership).

## Workflow

1. **Read the locked model** (+ the ADR-draft Forces table if present — volume and query patterns
   come from there). Ask only what the model and Forces table leave open.
2. **Skim existing models for conventions** (per @.claude/rules/models.md — base classes,
   column-vs-metadata for queried fields, indexes).
3. **Propose the schema projection** — tables, indexes, constraints, migration shape (**don't code**).
4. **Iterate to approval.**
5. **Output feeds the ADR's §4 Entities & Data Design** — the `/design-module` lane owns the
   `/create-adr` call. Only when run STANDALONE (no design-module rail) do you cap with `/create-adr`.
