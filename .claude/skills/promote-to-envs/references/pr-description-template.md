# Env Promotion PR Description Template

This is the canonical body format for CodeCommit PRs opened by `/promote-to-envs`. Render this template per target and pass the result to `aws codecommit create-pull-request --description`.

## Structure

```markdown
## Summary

<One-paragraph feature overview. Pull from `feature-context.md` "Summary" section if present, otherwise synthesize from the user stories / PRD referenced in the feature branch.>

## Companion PRs

<Markdown table of the other env PRs created in the same promote-to-envs run. Back-filled after all PRs are created in the session — the first PR will initially have an empty table; it is updated in Step 5 via `update-pull-request-description`.>

| Target Env | PR ID | URL |
|---|---|---|
| gamma | 14745 | https://ap-south-1.console.aws.amazon.com/codesuite/codecommit/repositories/crm-backend/pull-requests/14745 |
| tg-bn-uat | 14746 | https://ap-south-1.console.aws.amazon.com/codesuite/codecommit/repositories/crm-backend/pull-requests/14746 |

## Conflict Resolution Notes

<If there were no conflicts: "No conflicts — clean merge.">
<If there were conflicts: list each file and the resolution direction.>

- `path/to/file.py` — kept feature branch side (env drift on unrelated field)
- `other/file.py` — kept feature branch side (env had an older version of the same function)

## Test Plan

- [ ] Deploy integration branch to `<target>` env
- [ ] Smoke-test the primary user stories for the feature
- [ ] Verify no regressions on adjacent flows (list the specific flows)
- [ ] Check env-specific config (feature flags, secrets, cron triggers) still applies

## Deferred Findings

<If none: "No deferred findings.">
<If there are Medium/Low review items consciously deferred during the feature's dev loop, list them here with the rationale. Pull from `feature-context.md` "Deferred Findings" section if present.>

- [Medium] Refactor `X` interactor to extract Y helper — deferred to follow-up PR; non-blocking for current scope.
- [Low] Add integration test for edge case Z — deferred; unit coverage exists.
```

## Rendering Rules

- **Summary**: mandatory. Never blank — even trivial features need a one-line description.
- **Companion PRs**: starts empty for the first PR of a session; Step 5 of the skill updates all PRs via `update-pull-request-description` once every target's PR ID is known.
- **Conflict Resolution Notes**: mandatory section header, even if the value is "No conflicts — clean merge."
- **Test Plan**: minimum 3 checklist items. Prefer feature-specific over generic.
- **Deferred Findings**: mandatory section header, even if the value is "No deferred findings."

## Shell Quoting

The description is passed via `--description "<body>"`. When constructing the command:

- Write the rendered markdown to a temp file, then pass `--description file://<path>` to avoid shell-quoting hazards with backticks, dollar signs, and newlines in code blocks.
- Example:
  ```bash
  TMP_DESC=$(mktemp)
  cat > "$TMP_DESC" <<'EOF'
  ## Summary
  ...
  EOF
  aws codecommit create-pull-request \
    --region ap-south-1 \
    --title "Merge feature/<name> into <target>" \
    --targets repositoryName=crm-backend,sourceReference=feature/<name>-<target>,destinationReference=<target> \
    --description "file://$TMP_DESC"
  rm -f "$TMP_DESC"
  ```

## Update Operation (for companion back-fill)

```bash
aws codecommit update-pull-request-description \
  --region ap-south-1 \
  --pull-request-id <id> \
  --description "file://$TMP_DESC"
```
