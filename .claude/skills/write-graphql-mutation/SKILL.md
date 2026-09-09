---
name: write-graphql-mutation
description: Create a GraphQL mutation with proper error handling and interactor integration. Use when the user says "write a mutation", "create GraphQL mutation", "add mutation for feature", or needs a new Graphene mutation wired to an interactor with union response types.
argument-hint: "[mutation name or use case]"
disable-model-invocation: false
allowed-tools: Read, Grep, Glob, Write, Edit, Bash
---

# Write GraphQL Mutation

Create mutation for: $ARGUMENTS

Follow @.claude/rules/graphql.md and @.claude/rules/clean-architecture.md

## Workflow

1. If unclear on the use case, ask for clarification
2. Check if feature package exists in `sales_crm_graphql` — confirm with user
3. If not, get confirmation to create package skeleton (refer to existing packages)
4. Propose mutation schema (**don't code yet**)
5. Write the mutation
6. Integrate interactor with mutation
7. Handle all errors raised by the interactor
8. Self-review:
   - All interactor errors handled?
   - Uses `InputObjectType` for input?
   - Uses Union response types?
   - No business logic in resolver?
