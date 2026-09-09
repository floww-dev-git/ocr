# Coordinator Viability Research

**Research date:** 2026-07-29  
**Task:** Verify whether the `task-coordinator` agent's contract (drive one slice's multi-task dev loop end-to-end in a single invocation) is achievable given Claude Code's subagent runtime behavior.

---

## Question 1: Is there a documented limit on subagent turn count, runtime, or tool-use quota?

### Finding: Turn limits exist but enforcement is incomplete.

**maxTurns parameter**
- Subagents accept an optional `maxTurns` field (frontmatter or SDK `AgentDefinition`)
- If omitted, the subagent runs until completion or external stop
- **BUG:** The `maxTurns` field in agent frontmatter is **not enforced** in practice. A subagent declared with `maxTurns: 10` observed running 72+ turns before stopping. Reported as [issue #41143](https://github.com/anthropics/claude-code/issues/41143).

**Output token cap on subagents (undocumented)**
- Subagents have an 8000 output-token ceiling while the main loop is uncapped
- This creates an asymmetry: a subagent doing reasoning-heavy work (extended thinking) can exhaust its budget on thinking alone and produce zero output. Reported as [issue #78460](https://github.com/anthropics/claude-code/issues/78460).

**Turn mechanism**
- A "turn" = one agentic loop: Claude calls tools, receives results, decides next action, repeats until no tool calls
- The SDK counts tool-use turns only (not reasoning or output formatting)
- No documented hard runtime limit (no timeout per turn or per session)

**Implication:** There is no reliable turn cap to guarantee a subagent loops exactly N times then stops. The `maxTurns` parameter is advisory, not enforced. A long-running loop can theoretically continue indefinitely, but the 8000-token output cap on subagents creates a soft ceiling that may hit mid-task.

---

## Question 2: Can a subagent reliably loop through N sequential tasks in one invocation?

### Finding: Not by default; standard subagent semantics favor returning after one coherent unit.

**The observed reality (from manager memory, 2026-07-09 and 2026-07-16)**

The `task-coordinator` was designed to "run ONE slice's dev loop end-to-end" — roughly 5–10 sequential tasks, each spawning a developer, review, and commit. Observed behavior:
- Each coordinator spawn completed approximately **one task + its review**, then returned an idle notification
- The cycle did NOT auto-chain to the next task
- Workaround adopted: "budget one spawn per task-ish" + manual re-dispatch at boundaries

**Why this happens: subagent semantics**

Subagents (SDK [`query()` call returning `AgentDefinition`](https://code.claude.com/docs/en/agent-sdk/subagents)) are designed for **focused delegation of a single subtask**. The documentation examples show a subagent completing one analysis or fix, then returning its result to the parent. There is **no built-in sequencing mechanism** for a subagent to auto-chain through a list of sequential tasks without explicit re-dispatch.

A subagent completes when:
1. It produces a final message with no tool calls (natural completion), or
2. It hits `maxTurns` (if enforced), or
3. An API error cuts it off

Once it completes, it returns its result to the parent. There is no "continue to next task" instruction embedded in the subagent runtime — the parent must spawn a fresh subagent to proceed.

**The /goal command: designed for looping**

Claude Code offers the `/goal` command to drive persistent, condition-based loops. A `/goal` specifies what "done" looks like, and the runtime keeps looping (turn after turn) until that condition is met, checking after each turn whether the goal is satisfied. This is the **documented pattern for autonomous multi-turn work**.

However, `/goal` is a user-facing CLI command, not available inside a subagent's context (subagents are spawned from an `Agent` tool call with a fixed prompt, no REPL). So a subagent cannot use `/goal` to drive its own internal loop.

**Implication:** A subagent cannot reliably loop through N sequential subtasks in one invocation without additional orchestration. The subagent model expects single-subtask focus; multi-task looping requires either:
- The parent re-spawning a fresh subagent per task (defeats the purpose), or
- Using a higher-level primitive (see Question 5).

---

## Question 3: Can a subagent spawn its own subagents (nesting), and is there a depth cap?

### Finding: Yes, nesting is supported up to 3 levels (configurable, recently changed).

**Default depth**
- As of Claude Code v2.1.219, subagents can spawn subagents up to **3 layers below the root session** by default
- Controlled by environment variable `CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH`
- Setting it to `1` disables nesting entirely

**Historical context**
- v2.1.172–v2.1.216: subagents could nest up to 5 levels deep
- v2.1.217–v2.1.218: cap dropped to 1 (no nesting allowed by default)
- v2.1.219 onward: cap raised back to 3 (default)
- Source: [Claude Code subagents documentation](https://code.claude.com/docs/en/agent-sdk/subagents)

**The task-coordinator's claim**
The `.claude/agents/task-coordinator.md` states: "Depth-2 nesting is supported (fixed 5-level cap; you're at depth-1 spawning depth-2 workers — well within it). Confirmed against Claude Code sub-agents docs."

This claim is **outdated**. The document reflects an earlier version when the depth cap was 5. It is now 3, and a depth-1 coordinator spawning depth-2 developers is still within bounds.

**Implication:** The coordinator can spawn developer/reviewer/tester subagents (depth-2) from itself (depth-1) without hitting the nesting cap. The constraint is not depth, but the sequential-looping problem (Question 2).

---

## Question 4: What distinguishes idle notifications from final completion?

### Finding: The distinction is poorly defined; both fire ambiguously.

**Idle notification semantics**
- The harness fires `idle_notification` when a subagent or session reaches an idle state (Claude is waiting for user input)
- Documented triggers: `idle_prompt` event when Claude has completed a turn and is awaiting the next input

**Known issues**
Multiple bug reports show this is an open, unfixed problem:
- [Issue #29163](https://github.com/anthropics/claude-code/issues/29163): "Team agents go idle without responding or completing tasks" — agents emit idle_notification but haven't actually completed work
- [Issue #61547](https://github.com/anthropics/claude-code/issues/61547): "Agent tool: spawned sub-agents go idle immediately without executing prompt" — subagent fires idle on spawn before doing any work
- [Issue #45781](https://github.com/anthropics/claude-code/issues/45781): "Add BackgroundTasksIdle notification event" — user request to distinguish between "task is idle" and "task completed"

**The manager's observation (from memory)**
- Idle notification was conflated with "agent died" — causing duplicate re-spawns
- Actual state was on disk (git log, tick counts) — idle_notification told you nothing
- The harness provides no status field to distinguish "returned because it finished" from "returned because it's waiting for input"

**Implication:** There is **no reliable way to distinguish a finished subagent from one that is idle and waiting**. You must poll disk state (git commits, file timestamps) to determine actual progress. An idle_notification could mean:
- The subagent completed a coherent task and is done (returned final result)
- The subagent hit a blocker and is waiting for input
- The subagent crashed or hung
- (In the coordinator's case) the subagent completed one task and is idling before auto-chaining to the next — **but auto-chaining doesn't happen by default**

---

## Question 5: Are there better-supported primitives for driving a long multi-task loop while keeping the parent's context small?

### Finding: Yes; several patterns are documented and battle-tested.

### Pattern A: Multi-session task coordination (native, recommended)

Claude Code v2.1.200+ includes **native task management with multi-session coordination**:

- Define a shared task list (file-based or via CLAUDE_CODE_TASK_LIST_ID environment variable)
- Multiple independent sessions point at the same task list
- Each session picks up a task, marks it complete, then moves to the next
- Updates "broadcast" to all active sessions via the shared state

**Advantage:** Each session is stateless (can be killed/restarted); the task list is the single source of truth. No coordinator needs to hold the entire slice's context.

**Example pattern (Writer/Reviewer):**
- Session 1: reads task, implements, commits, marks complete
- Session 2: (fresh context) reads same task list, sees task marked done, moves to next, reviews

This distributes load and keeps individual session contexts small.

**Documentation:** [Claude Code task management](https://claudefa.st/blog/guide/development/task-management) (unofficial blog post, but reflects v2.1.200+ reality).

### Pattern B: /goal and /loop CLI commands (for fully autonomous runs)

- `/goal <condition>` — tell Claude Code what "done" looks like
- `/loop <interval>` — tell Claude to keep working on a recurring interval
- The runtime checks the goal after each turn; if met, stops; if not, continues with a reason

**Advantage:** True looping is built in; you don't need to coordinate subagent re-spawns manually.

**Limitation:** This is a top-level CLI feature, not available inside a subagent's context. A subagent cannot use `/goal` to loop internally.

**Documentation:** [/goal and /loop guide](https://www.mindstudio.ai/blog/how-to-use-goal-and-loop-claude-code-autonomous-workflows).

### Pattern C: Workflow tool (for very large orchestrations)

For orchestrating 10s–100s of agents, the `Workflow` tool lets you move orchestration into a script that runs outside the conversation context.

**Advantage:** No conversation bloat; workflow state is tracked in the script, not the turn history.

**Limitation:** Requires TypeScript Agent SDK v0.3.149+. Not a built-in Claude Code feature.

**Documentation:** [Dynamic workflows](https://code.claude.com/docs/en/agent-sdk/workflows) (SDK docs).

### Pattern D: Single-writer + disk state (what the repo currently uses)

The repo adopted: one task-coordinator per slice, re-spawning at task boundaries, with disk as the coordination channel (tasks YAML file, feature-context, git commits).

**Advantage:** Works with current harness; no new infrastructure.

**Limitation:** Requires manual re-dispatch; per-task spawns accumulate context cost ("budget one spawn per task").

**Documentation:** Implicit in `.claude/agents/task-coordinator.md` Harness Notes and manager memory.

---

## Verdict

### Is the task-coordinator's premise achievable as designed?

**No, not as currently designed. It is unsound given the runtime.**

### Why

1. **Subagents don't auto-loop through sequential tasks.** The subagent model completes after a coherent unit of work (typically ~1 task). There is no built-in mechanism to auto-chain to the next task without a parent re-spawn.

2. **Idle notifications don't signal completion.** You cannot distinguish a finished subagent from an idle one via notifications alone. Disk polling is required.

3. **The /goal pattern isn't available inside subagents.** A subagent cannot use `/goal` to drive its own internal loop; that's a top-level CLI feature.

4. **The maxTurns enforcement is broken.** Even if you tried to gate a subagent with `maxTurns: <N>`, it would not be honored.

### Salvageable? Yes, with a design change.

**Recommended approach: Replace the single-coordinator model with multi-session task coordination:**

1. Define a shared task list (or CLAUDE_CODE_TASK_LIST_ID)
2. Spawn **stateless**, independent developer/reviewer/tester sessions, each handling one task
3. Sessions read the shared task list, mark tasks complete, and exit
4. Orchestration lives in the task file, not in a long-lived coordinator

**Advantages:**
- Each session is small and restartable
- The task list is the single source of truth
- No idle-notification ambiguity (each session completes or fails cleanly)
- Scales to any number of tasks (within concurrent session limits)
- Aligns with Claude Code v2.1.200+ native task management

**Trade-off:**
- Requires reworking the dispatch model (manager spawns N independent sessions instead of ONE coordinator)
- CLI changes to point sessions at a shared task list

**Alternative (lower-impact): Acknowledge the boundary and re-dispatch.**

Keep the coordinator but:
- Document that each spawn drives ~1 task (+ its review)
- Codify the re-dispatch pattern in the manager's between-gate loop
- Use disk state (tick counts) to detect completion, not idle_notification
- Budget token/time costs accordingly

This is lower-effort than multi-session refactoring but caps the coordinator's value: it becomes "orchestrate one task + review," not "orchestrate a whole slice."

---

## Sources

- [Claude Code subagents documentation](https://code.claude.com/docs/en/agent-sdk/subagents)
- [Issue #41143: maxTurns frontmatter not enforced](https://github.com/anthropics/claude-code/issues/41143)
- [Issue #78460: Subagent 8000 token output cap](https://github.com/anthropics/claude-code/issues/78460)
- [Issue #29163: Team agents go idle without responding](https://github.com/anthropics/claude-code/issues/29163)
- [Issue #61547: Sub-agents go idle immediately without executing](https://github.com/anthropics/claude-code/issues/61547)
- [Issue #45781: BackgroundTasksIdle notification request](https://github.com/anthropics/claude-code/issues/45781)
- [Claude Code task management guide](https://claudefa.st/blog/guide/development/task-management)
- [/goal and /loop commands guide](https://www.mindstudio.ai/blog/how-to-use-goal-and-loop-claude-code-autonomous-workflows)
- [Claude Code /goal: Stop Babysitting Your AI Agent](https://aimaker.substack.com/p/claude-code-goal-command-finish-line)
- [Workflow tool documentation](https://code.claude.com/docs/en/agent-sdk/workflows)
- [How the agent loop works](https://code.claude.com/docs/en/agent-sdk/agent-loop)
