---
name: data-loading
description: Implement a data loading workflow for CRM entities from CSV/JSON/ZIP files. Use when the user says "load data", "import CSV", "bulk upload", "data migration from file", or needs to ingest external data into CRM entities.
argument-hint: "[entity type and data source description]"
disable-model-invocation: false
allowed-tools: Read, Grep, Glob, Write, Edit, Bash
---

# Data Loading

Implement data loading for: $ARGUMENTS

Follow @.claude/rules/clean-architecture.md and @.claude/rules/interactors.md

## Workflow

1. **Understand the use case:**
   - Entities involved in the data loading
   - CSV/JSON/ZIP format and cell data format
   - Operation types per entity (create, update, delete, create/update)
2. **Understand business rules** per entity:
   - Required fields, unique constraints, relationship constraints
   - Domain-specific rules (e.g. order amount > 0, template-stage same pipeline)
3. **Ask clarifications** → wait → integrate → repeat if needed
4. **Validate key decisions** with user:
   - Models involved
   - Data conversion from source to models
   - Data consistency (updates, creates, limitations)
   - Volume → sync vs async loading
5. **Propose validations** (input validation, relation validation, JSON schemas)
6. **Study existing patterns:**
   - `sales_crm_graphql.data_loading_requests.mutations.csv.initiate_data_loading_request_from_csv.InitiateDataLoadingRequestFromCSV`
   - `sales_crm_core.populate.populate_layout_tabs.populate_layout_tabs.PopulateTabsInteractor`
   - `sales_crm_core.interactors.layouts.update_or_create_tab_from_data_loading.UpdateOrCreateTabFromDataLoadingInteractor`
   - Integrate new loading into the existing mutation
7. **Self-review** — covers all requirements, follows DRY with existing interactors/DTOs
8. **Propose ADR** → get approval → implement
