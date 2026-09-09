---
name: feature-init
description: Bootstrap a new feature with git worktree, feature branch, and feature context file. Use when starting a new feature.
argument-hint: "[feature name]"
disable-model-invocation: false
allowed-tools: Read, Bash, Write, Glob
---

# Initialize New Feature

Bootstrap feature: $ARGUMENTS

## Process

1. **Validate feature name**
   - Convert to kebab-case if needed
   - Check no existing worktree/branch with this name: `git worktree list` and `git branch --list`

2. **Create worktree and branch**
   ```bash
   git worktree add ../feature-$ARGUMENTS -b feature/$ARGUMENTS
   ```

3. **Create feature context file** at the worktree root:
   ```markdown
   # Feature: $ARGUMENTS

   Branch: feature/$ARGUMENTS
   Created: [today's date]
   PRD: [ask user for link or path]
   ADR: [pending]
   Task List: [pending]

   ## Current Phase
   [x] Planning → [ ] Architecture → [ ] ADR → [ ] Tasks → [ ] Implementation → [ ] Review → [ ] Merged

   ## Active Task
   Task: Initial planning
   Stage: planning
   Status: not started

   ## Completed Tasks
   (none yet)

   ## Pending Tasks
   - [ ] Analyze PRD and create user stories
   - [ ] Design architecture
   - [ ] Write ADR
   - [ ] Generate task list

   ## Notes for Next Session
   - Feature just initialized, start with PRD analysis
   ```

4. **Report to user**
   - Confirm worktree created at `../feature-$ARGUMENTS`
   - Confirm branch `feature/$ARGUMENTS` created
   - Next step: switch to the worktree and invoke `architect` for planning
