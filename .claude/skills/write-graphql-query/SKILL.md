---
name: write-graphql-query
description: Create a GraphQL query with resolver and interactor integration. Use when the user says "write a query", "create GraphQL query", "add query endpoint", or needs a new Graphene query with resolver, DataLoader integration, and permission checks.
argument-hint: "[query name or use case]"
disable-model-invocation: false
allowed-tools: Read, Grep, Glob, Write, Edit, Bash
---

# Write GraphQL Query

Create query for: $ARGUMENTS

Follow @.claude/rules/graphql.md and @.claude/rules/clean-architecture.md

## Workflow

1. If unclear on the use case, ask for clarification
2. Check if feature package exists in `sales_crm_graphql` — confirm with user
3. If not, get confirmation to create package skeleton (refer to existing packages)
4. Propose query schema (**don't code yet**)
5. Write resolver in the resolvers package
6. Integrate interactor with resolver
7. Handle all errors raised by the interactor
8. Integrate resolver with query
9. Self-review:
   - All interactor errors handled?
   - Uses DataLoaders for N+1 prevention?
   - Permission checks via user context?
   - No business logic in resolver?
