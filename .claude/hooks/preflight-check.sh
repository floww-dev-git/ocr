#!/bin/bash
# PreToolUse hook for Bash: warns when committing without running self-review-checklist
# Profile: standard+ (skipped in minimal)
PROFILE="${CLAUDE_HOOK_PROFILE:-standard}"
if [[ "$PROFILE" == "minimal" ]]; then exit 0; fi

INPUT=$(cat)
COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // empty')

# Only intercept git commit commands
if echo "$COMMAND" | grep -qE '^\s*git\s+commit'; then
    # Check if there are staged changes
    STAGED=$(git diff --cached --name-only 2>/dev/null | head -1)
    if [ -n "$STAGED" ]; then
        echo "REMINDER: Ensure you ran /self-review-checklist before committing."
        echo "Top issues to verify: DRY violations, error handling in delegating methods, null guards, cross-app imports."

        # Check for staged GraphQL files that require schema regeneration
        GQL_FILES=$(git diff --cached --name-only 2>/dev/null | grep -E '(sales_crm_graphql/|ext_client_graphql/|/mutations/|/queries/)' | head -5)
        if [ -n "$GQL_FILES" ]; then
            echo ""
            echo "BLOCKING: Staged files touch GraphQL paths — regenerate schemas before committing:"
            echo "  python manage.py schema_gen --schema sales_crm_graphql.schema.schema"
            if echo "$GQL_FILES" | grep -q 'ext_client_graphql/'; then
                echo "  python manage.py schema_gen --schema ext_client_graphql.schema.schema --out ext_client_schema --schema_enum EXT_CLIENT_SCHEMA"
            fi
            echo "Then stage the regenerated schema files."
        fi
    fi
fi

exit 0
