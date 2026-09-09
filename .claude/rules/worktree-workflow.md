# Worktree Workflow

Worktrees are OPTIONAL — the default workflow is feature branches on a single checkout, where
the tracked `feature-context.md` in `<app>/docs/features/<slug>/` makes a branch switch a
context switch (see the `feature-context.md` rule). Use a worktree when two features must be
worked in parallel.

## Convention
- One git worktree per feature — no two features share a worktree
- Branch naming: `feature/<name>` (kebab-case)
- Worktree creation: `claude --worktree feature/<name>` or via `/feature-init`

## Isolation Rules
- All code changes for a feature stay within its worktree
- Never commit to another feature's branch from the wrong worktree
- Each worktree has its own Claude session with independent context
- `.claude/` config is shared across worktrees (same repo)

## Merge-Back Cadence
- Pull from the target branch (e.g., `alpha`) into the feature branch regularly
- At minimum: before starting a new task, and before creating a PR
- Resolve merge conflicts within the feature worktree, never on the target branch

## Cleanup
- After a feature is merged, remove the worktree: `git worktree remove <path>`
- Delete the merged feature branch: `git branch -d feature/<name>`
- The `manager` agent tracks active worktrees and flags stale ones

## Feature Context File
- Every feature has ONE `feature-context.md` at `<owning_app>/docs/features/<slug>/` (tracked —
  it travels with the branch, worktree or not)
- Updated after each completed task and at session end
- Read at session start to restore context
- See `feature-context.md` rule for location and format requirements
