---
name: feature-switch
description: Context-switch to another feature's worktree. Saves current feature context and loads the target feature's context.
argument-hint: "[feature name to switch to]"
disable-model-invocation: false
allowed-tools: Read, Bash, Write, Glob
---

# Switch Feature Context

Switch to: $ARGUMENTS

## Process

1. **Save current feature context**
   - Find `feature-context.md` in current worktree
   - Update it with: current active task, stage, any progress made this session
   - If no context file exists, skip (not in a feature worktree)

2. **Locate target worktree**
   - Check `git worktree list` for a worktree matching `feature/$ARGUMENTS`
   - If not found, ask user if they want to create it via `/feature-init`

3. **Load target feature context**
   - Read `feature-context.md` from the target worktree
   - Extract: current phase, active task, completed tasks, pending tasks, notes

4. **Brief the developer**
   ```
   Switched to: feature/$ARGUMENTS
   Phase: [current phase]
   Last completed: [last completed task]
   Next task: [next pending task]
   Blockers: [any blockers]
   Notes: [notes for this session]
   ```

5. **Instruct developer** to change to the worktree directory:
   ```bash
   cd ../feature-$ARGUMENTS
   ```
