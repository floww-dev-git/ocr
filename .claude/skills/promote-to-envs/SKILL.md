---
name: promote-to-envs
description: Promote a pushed feature branch to selected environment branches by creating per-env feature branches, merging, and opening CodeCommit pull requests. Use after the dev-loop push gate is confirmed complete, or when the user says "promote to envs", "raise env PRs", "open env PRs", "promote feature", or "merge to envs".
argument-hint: "[optional: comma-separated target env branches, or 'all']"
disable-model-invocation: false
allowed-tools: Read, Grep, Glob, Bash
---

# Promote to Environment Branches

Promote: $ARGUMENTS

## Purpose

After a feature branch has been pushed to `origin/feature/<name>`, create per-environment integration branches and open CodeCommit pull requests against each selected environment. This skill automates a mechanical sequence we previously ran 3+ times per feature by hand.

## Ownership

- **Manager** prompts the user with the env checklist after push confirmation.
- **Developer** executes the git + AWS CLI mechanics for each selected target.
- **Main session** routes the prompt to manager, then delegates execution to developer.

## Inputs

Required:
1. **Feature branch name** — `feature/<name>` (auto-detect from current branch if the dev is already on it)
2. **Target env selection** — one or more of: `alpha`, `beta`, `gamma`, `tg-bn-gamma`, `tg-bn-uat`

Derived:
- Per-env integration branch name: `feature/<name>-<target>` (e.g., `feature/tdr-gamma`)
- PR title: `Merge feature/<name> into <target>`
- PR destination: the env branch
- PR source: `feature/<name>-<target>`

## Canonical Env Branch List

Exactly these five, in this order:

1. `alpha`
2. `beta`
3. `gamma`
4. `tg-bn-gamma`
5. `tg-bn-uat`

### Why `tg-bn-prod` is NOT on this list

`tg-bn-prod` is the production branch for the TG/BN tenant. Promotion to prod is a separate release-management step (deployment window, change management, sign-off) — it does NOT happen as part of the normal feature-push flow. Do not add `tg-bn-prod` to this list. If a future workflow needs prod promotion, build a separate skill with explicit approval gates.

## Repository Details

- **VCS host:** AWS CodeCommit (NOT GitHub) — use `aws codecommit`, not `gh`
- **Repo name:** `crm-backend`
- **Region:** `ap-south-1`
- **PR URL format:** `https://ap-south-1.console.aws.amazon.com/codesuite/codecommit/repositories/crm-backend/pull-requests/{id}`

## Workflow

### Step 1 (Manager) — Prompt for target envs

Immediately after the push gate is confirmed complete, manager asks the user **exactly one** question (per `consent-granularity.md` — this is the sole gate for this skill):

> Feature pushed to `feature/<name>`. Which env branches need a PR?
>
> 1. `alpha`
> 2. `beta`
> 3. `gamma`
> 4. `tg-bn-gamma`
> 5. `tg-bn-uat`
>
> Reply with a comma-separated list, `all`, or `none`.

Parse the response:
- `none` → skill ends. Return dev to the original feature branch (no-op since they are already there).
- `all` → targets = all five env branches.
- Comma-separated list → intersect with the canonical five. Reject any unknown branch with a clear error; do not silently drop.

Hand off to developer with the resolved target list.

### Step 2 (Developer) — Verify preconditions

Before executing the mechanical sequence for any target:

1. Confirm the current branch is `feature/<name>` and the working tree is clean (`git status --porcelain` returns empty).
2. Confirm `origin/feature/<name>` exists and matches the local branch (the push gate should have ensured this, but verify).
3. Announce the target list and the order of execution. Execute targets sequentially in the order given.

### Step 3 (Developer) — Per-target mechanical sequence

For each selected target (e.g., `gamma`):

```bash
# 1. Fetch latest env branch from origin
git fetch origin <target>

# 2. Create per-env integration branch from origin/<target>
git checkout -b feature/<name>-<target> origin/<target>

# 3. Merge the feature branch in (no editor, use default message)
git merge feature/<name> --no-edit
```

#### 3a. Conflict resolution default

If `git merge` reports conflicts:
- **Default direction: keep the feature branch side** (i.e., `git checkout --theirs <file>` when merging INTO env branch — because the env branch is checked out, `theirs` = the feature branch we are merging in).
- **Announce-and-execute** per `consent-granularity.md`: state "Resolving N conflicts toward feature side. Files: <list>. Reply to override." Then resolve, `git add` the resolved files, and continue.
- If a conflict is clearly NOT a feature-vs-env drift conflict (e.g., two independent features both touched the same line for unrelated reasons), pause and ask the user before resolving. This is a genuine judgment call, not a packaging decision.

#### 3b. Commit the merge

```bash
git commit --no-edit
```

**If pre-commit hooks (e.g., black, ruff) reformat files and the commit fails:**
- **Default: re-stage the reformatted files and retry the commit WITHOUT `--no-verify`.** Hooks exist for a reason; bypassing them creates dirty branches.
- Announce: "Pre-commit reformatted `<files>`. Re-staging and retrying commit."
- Retry: `git add <reformatted-files>` then `git commit --no-edit`.
- If the hook fails for a reason other than reformatting (e.g., a lint error that black did not fix), stop and report — do NOT use `--no-verify` to force it through.

#### 3c. Push the integration branch

```bash
git push -u origin feature/<name>-<target>
```

#### 3d. Create the CodeCommit PR

```bash
aws codecommit create-pull-request \
  --region ap-south-1 \
  --title "Merge feature/<name> into <target>" \
  --targets repositoryName=crm-backend,sourceReference=feature/<name>-<target>,destinationReference=<target> \
  --description "<rendered description — see references/pr-description-template.md>"
```

Capture the `pullRequestId` from the JSON response. **Immediately** construct the full clickable URL:

```
https://ap-south-1.console.aws.amazon.com/codesuite/codecommit/repositories/crm-backend/pull-requests/{pullRequestId}
```

**CRITICAL (recurring user frustration):** Both the PR ID AND the full URL must be stored and reported. The final table presented to the user MUST include the complete URL in every row — returning only the PR ID is not acceptable.

#### 3e. Accumulate PR record

Collect `(target, pr_id, full_url)` into a running list — the `full_url` is the complete CodeCommit console URL constructed above, not a placeholder. After all targets are processed, this list is rendered as a table for the user (with full clickable URLs in every row) AND back-filled into each PR's "Companion PRs" section where possible. See Step 5.

### Step 4 (Developer) — Return to original branch

After ALL targets are processed (success or otherwise):

```bash
git checkout feature/<name>
```

The per-env integration branches (`feature/<name>-<target>`) remain locally and on origin — they are the PR source branches and must not be deleted until the PRs merge.

### Step 5 (Developer) — Report to the user

Post a single message with:

1. A markdown table of created PRs — **every row MUST have the full clickable URL, never abbreviated**:

   | Target | PR ID | URL |
   |---|---|---|
   | gamma | 14745 | https://ap-south-1.console.aws.amazon.com/codesuite/codecommit/repositories/crm-backend/pull-requests/14745 |
   | tg-bn-uat | 14746 | https://ap-south-1.console.aws.amazon.com/codesuite/codecommit/repositories/crm-backend/pull-requests/14746 |
   | tg-bn-gamma | 14747 | https://ap-south-1.console.aws.amazon.com/codesuite/codecommit/repositories/crm-backend/pull-requests/14747 |

2. A short status note: "Returned dev to `feature/<name>`. Integration branches preserved on origin."
3. Any conflicts that were resolved, with the files touched.
4. Any targets that failed (e.g., AWS CLI error, merge aborted) with the reason.

#### Companion PRs back-fill

If the user runs this skill for multiple targets in one session, the first PR created will not know about the later PRs' URLs. After all PRs are created, update each PR's description to include the full companion list:

```bash
aws codecommit update-pull-request-description \
  --region ap-south-1 \
  --pull-request-id <id> \
  --description "<updated description with full companion table>"
```

Announce-and-execute: "Back-filling companion PR links across N PRs." Do not ask.

## Error Handling

- **`git fetch` fails** — report and abort the skill. Do not proceed to other targets (network issue affects all).
- **`git checkout -b` fails because branch already exists** — this indicates a prior run that was not cleaned up. Pause and ask the user: delete existing local branch and retry, or skip this target. Do NOT auto-delete.
- **`git merge` fails for non-conflict reasons** (e.g., detached HEAD) — abort the skill, report, restore the dev to `feature/<name>`.
- **`aws codecommit create-pull-request` fails** — report the AWS error verbatim. Common causes: expired credentials, destination branch does not exist on origin, source already has an open PR against that destination. Do NOT retry blindly; surface the error and let the user decide.
- **Partial success** — if targets 1 and 2 succeed and target 3 fails, still report the successful PRs in the final table and flag target 3 separately. Do not roll back successful PRs.

## PR Description Template

See `references/pr-description-template.md` for the exact structure. Required sections:

- **Summary** — one-paragraph feature overview (pulled from feature-context.md if present)
- **Companion PRs** — markdown table of the other env PRs created in the same session (back-filled in Step 5)
- **Conflict Resolution Notes** — files where conflicts were resolved and the resolution direction
- **Test Plan** — checklist of how to verify the feature on this env
- **Deferred Findings** — any Medium/Low review items that were consciously deferred (pulled from feature-context.md if present)

## What This Skill Does NOT Do

- Does NOT run tests on the integration branch. The feature branch was already tested before push; the env merge is purely a propagation step. If a test suite failure is expected on a specific env due to env-specific config, that is a separate concern.
- Does NOT promote to `tg-bn-prod`. See "Why `tg-bn-prod` is NOT on this list" above.
- Does NOT approve or merge the PRs. Opening the PR is the deliverable; approval is a separate human review step.
- Does NOT delete the per-env integration branches. They remain until the PR merges.

## Consent Granularity

This skill has **exactly one** question: the env checklist at Step 1. Every other decision inside the skill is announce-and-execute:

| Sub-decision | Default | Announce as |
|---|---|---|
| Conflict resolution direction | Feature side | "Resolving N conflicts toward feature side. Files: <list>. Override to halt." |
| Pre-commit reformat re-stage | Re-stage and retry without `--no-verify` | "Pre-commit reformatted `<files>`. Re-staging and retrying." |
| Proceed to next target after current succeeds | Proceed | "Target `<a>` done. Moving to `<b>`." |
| Companion PRs back-fill | Run after all PRs created | "Back-filling companion links across N PRs." |
| Return to original feature branch at end | Checkout `feature/<name>` | "Returning dev to `feature/<name>`." |

## Related Rules and References

- `@.claude/rules/consent-granularity.md` — governs the announce-and-execute pattern used throughout
- `@.claude/rules/dev-loop.md` — the Feature Lifecycle includes a "Promote to envs" step after push
- `@.claude/rules/references/agent-teams-pipeline.md` — auto-chain entry for post-push promotion
- `@.claude/skills/promote-to-envs/references/pr-description-template.md` — PR body template
