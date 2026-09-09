# Feature KT Document — Template

Copy this skeleton. Fill each section. Keep every section ≤ 50 lines (the diagram is exempt). Delete these instruction comments before saving.

---

```markdown
# Feature KT: <Feature Name>

**Owning App:** <django app>
**Branch / ADR:** <feature/branch-name> · <ADR ref if any>
**Date:** <today>
**Author:** <you>

## 1. Problem / Usecase

<Who hurt, and why. The real-world need in business terms — not the code. 2-5 lines.>

## 2. Solution

<What we built, plainly. What the user/system can now do that they could not before.
The key idea, not the implementation tour. ≤ 50 lines.>

## 3. Solution Flow Diagram

<One merged diagram, OR separate per-actor diagrams — whichever is clearer.
SYSTEM is an actor whenever a step happens without a human (jobs, schedulers,
event handlers, lazy transitions, get-or-create). Do not omit it. No line limit.>

\```mermaid
sequenceDiagram
    actor Officer as Officer
    participant System
    participant Records as Licence Records

    Officer->>System: Upload the LTP list (spreadsheet)
    System->>System: Check the file and every row
    loop For each LTP in the file
        alt Already has a licence
            System->>Records: Update their details
        else New licence
            System->>Records: Create the licence
        end
    end
    System-->>Officer: Result file (succeeded / partial / failed)
\```

## 4. Configuration Changes Required

<Every config change, each with a SAMPLE and a one-line explanation. If none: "None.">

- **<config item>** — <what it is, one line>.
  Sample:
  \```
  <csv header row / action name / toggle key / pipeline id>
  \```

## 5. Breaking Changes

### Config breaking
<Configs/CSVs/toggles that now behave differently or are now required. If none: "None.">

### Tech / Code breaking
<API contract changes, removed/renamed fields, changed enums, migration impacts,
behaviour changes downstream depends on. If none: "None.">

## 6. Config Checkpoints / Decisions Taken

<Deliberate config decisions, defaults, and guardrails the team locked in — and why.
What the business should know was decided. NOT pending work. One line each.>

- <decision — what was chosen, and the reason / guardrail it sets>

## 7. Tech Debt

<Knowingly deferred, half-done, or owed work (technical or config) — faithful to the ADR's
"Deferred" list and TODOs in code. Frank. One line each.>

- <deferred item — what's missing and the current stopgap>
```

---

## Diagram cheats

- **Business audience** — plain-language actors and steps only. No service/class/interactor names, no rule-set or field-reference ids in the picture. "System recognises the licence", not the call that does it.
- **sequenceDiagram** — actor↔system message exchange over time (most KT flows). Use `actor` for humans, `participant` for systems/services.
- **flowchart TD** — decision/branch-heavy flows with no strong time axis.
- Keep labels short. Group system-internal steps as self-messages (`Sys->>Sys: validate`).
- Multiple actors with different journeys → consider one `sequenceDiagram` per actor under H3 sub-headings, OR a single merged diagram if they share a backbone.
