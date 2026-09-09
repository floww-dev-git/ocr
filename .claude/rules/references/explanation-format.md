# Code Explanation Format

When the user asks to explain a file, script, module, function, or any piece of code — use the structure below. Applies to phrasings like "explain this", "walk me through X", "how does Y work", "help me understand Z". Applies to every agent and the main session.

## Base Structure — First-Pass Explanation (Required Sections, in this order)

1. **Problem Statement** — 1-2 lines. The real-world need this code serves, from the user's point of view, not the code's.
2. **Constraints & Givens** — bullets. The non-negotiables shaping the design: permissions, latency, memory, third-party limits, what's available vs forbidden. Without this, the "why" of the design is invisible.
3. **Core Idea / Key Insight** — 1-2 lines. The single trick or approach that makes the solution work under the constraints. The one-sentence takeaway.
4. **Execution Flow — Bird's Eye** — numbered list, 3-7 steps. End-to-end pipeline as `Input → Step A → Step B → ... → Output`. No details, just the shape. This is the mental-model scaffold.
5. **Step-by-Step Deep Dive** — one block per step from section 4. For each step include:
   - Purpose — what this step is responsible for
   - Input → Output — what comes in, what goes out
   - How it works — mechanism in 2-4 lines
   - Why this way — design choice if non-obvious
   - Gotchas — edge cases, tricky bits
6. **Outputs & Side Effects** — bullets. Files produced, exit codes, logs, state changes. For consumers of the output.
7. **Hooks for Downstream Use** — only when the code feeds a larger workflow. What artifacts flow to later stages. Skip for standalone code.

## Deep-Dive Variants (Optional — trigger on follow-up drill-down)

Use these when the user asks to go deeper on a specific step or runtime behaviour after a first-pass explanation. Do NOT use them for the first-pass response. Pick the variant that matches the ask — occasionally combine both if the user wants concepts AND a trace.

### Variant A — Concept → Code Mapping Table
Trigger phrasing: "explain step N in detail", "how does the [async/socket/event-loop/etc.] part work", "what's actually doing the work here".
Use when the code leans on abstract primitives (asyncio, sockets, threads, generators, signals, event loops, etc.) and the user needs to see that the script is mostly wiring and the library does the heavy lifting.

Required table columns:
| Concept | Where it lives in the script | Who actually implements it |

- One row per primitive the reader must understand.
- "Where it lives" — exact function call, line number, or token. Be specific.
- "Who implements it" — user code vs named library/kernel/runtime. This is the insight.
- Follow the table with a short paragraph on what this tells the reader (usually: "the script is glue; the library is the engine").

### Variant B — Single-Instance Lifecycle Trace
Trigger phrasing: "trace a single X", "walk me through one [request/worker/task/job]", "what happens to one specific [instance]".
Use when the user wants to understand runtime behaviour by following ONE concrete instance end-to-end, not the flow in the abstract.

Required structure:
- Pick ONE instance with fake-but-realistic inputs (e.g., "worker #17 out of 5000, key = `uploads/abc.pdf`").
- Numbered named stages covering its full lifecycle (Born → Scheduled → Running → Parked → Woken → Returns → Harvested → GC'd, or the equivalent for the domain).
- For each stage, describe: what's in memory, what's happening in the outside world (OS, network, DB), and any state transition.
- Close with a compressed table — columns: `Time (T=Xms) | Event | State | CPU usage` (or the domain-appropriate resource column).
- End with a one-paragraph "day-in-the-life" mental model — slightly poetic is fine; the goal is a sticky image, not a spec.

## Hard Rules

- Never do a line-number walkthrough or top-to-bottom prose dump — it forces sequential reading and blocks mental-model formation.
- Organize section 5 by responsibility, not source order.
- Section 7 is optional — omit for standalone code.
- Section 6 may fold into the last step of section 5 if trivial.
- Deep-dive variants are follow-up-only — never emit them on the first explanation request.
- Read the code before explaining it (per `investigate-before-answering.md`). Never explain from the filename or imports alone.
- For Variant A, line numbers and function names must be verified against the file — no fabricated line numbers.
- For Variant B, the chosen instance must be plausible for the system's actual inputs — no impossible scenarios.
- Keep each section tight. Length comes from coverage, not padding.
