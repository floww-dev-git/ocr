---
globs:
  - ".claude/**"
---

# Config Observation & Protection

## Config File Protection

Do not create or modify `.claude/` config files (rules, skills, agents) directly — delegate to the `dhruva` agent first. It checks for overlap, enforces conventions, and ensures best practices. Agent routing to dhruva for config requests is handled by the `agent-delegation` rule.

## Continuous Observation (always active)

While working on ANY task, continuously watch for opportunities to improve the `.claude/` configuration. After completing a task or noticing a pattern, proactively suggest to the user when you observe:

- **Repeated manual steps** → could become a **skill** (workflow automation)
- **Corrections you keep making** → could become a **rule** (enforce automatically)
- **Domain knowledge you had to look up** → could become a **folder CLAUDE.md** or **memory**
- **Complex decisions requiring judgment** → could become an **agent** (persona with decision framework)
- **Recurring debugging patterns** → could become **agent memory** (persistent insights)
- **File-specific conventions** → could become a **path-scoped rule** (targeted enforcement)
- **External API patterns** → could become a **reference file** in an existing skill
- **Review feedback that recurs** → could become a **rule** (prevent at authoring time)

**How to suggest:** At the end of a task or when you spot a pattern, briefly mention it:
> "I noticed [pattern]. This could be captured as a [rule/skill/agent/memory] so it's enforced automatically. Want me to set it up?"

Keep suggestions lightweight — one line, not a full proposal. Only elaborate if the user says yes, at which point delegate to dhruva.

## Folder CLAUDE.md Convention

Domain context lives in folder `CLAUDE.md` files, NOT skills. Skills are for workflows/processes ONLY.

- Every Django app SHOULD have a `CLAUDE.md` at its root with: scope boundary, dependencies, key entities, state machines, business rules, gotchas
- Sub-folders MAY have their own `CLAUDE.md` but ONLY for packages with non-obvious domain knowledge. Most packages don't qualify — the folder name + code is sufficient.
- Claude auto-loads folder `CLAUDE.md` when touching files in that directory — no skill invocation needed
- **Skills = workflows** (step-by-step processes, implementation guides). **Folder CLAUDE.md = domain reference** (entities, rules, relationships)
- Never create "context-loader" skills — that pattern creates bloat
- After implementing a feature that adds new interactors, models, or changes app architecture, flag Dhruva to update the app's `CLAUDE.md`. For new apps and significant new modules, this is a hard gate — see `ai-readiness-gate.md`
- After a feature is merged, Dhruva checks if any app `CLAUDE.md` needs updating

### Quality Standards
- **Litmus test**: for every line, ask "Would removing this cause Claude to make a wrong decision?" If no, cut it.
- **Size targets**: 80 lines per app (hard limit 250). Sub-folder: 40 lines (hard limit 100).
- **Anti-patterns**: no fabricated code, no directory listings, no marketing copy, no pattern tutorials, no file-by-file descriptions.
- **Content guide**: see `.claude/skills/write-app-claude-md/references/claude-md-content-guide.md` for the full standard.
- **Gold standard**: `payments_engine/CLAUDE.md` — use as template reference.

### Subfolder CLAUDE.md Threshold
Do NOT create a subfolder `CLAUDE.md` unless it contains 20+ lines of genuinely non-obvious domain knowledge not already covered in the app-level `CLAUDE.md`. If a subfolder `CLAUDE.md` drops below this threshold after trimming, delete it and fold the relevant content up to the app level. Most subpackages do not qualify — folder name + code + app-level context is sufficient.

**Top candidates for future trim/deletion** (small and likely redundant with app-level context — policy only, no action this pass):
- `layouts/CLAUDE.md` (16 lines)
- `tdr/interactors/digitalization/CLAUDE.md` (18 lines)
- `sales_crm_core/interactors/custom_objects/CLAUDE.md` (20 lines)
- `sales_crm_core/interactors/views/CLAUDE.md` (20 lines)
- `tdr/interactors/letters/CLAUDE.md` (20 lines)

### Proactive Maintenance Signals
When any of these occur, it indicates missing domain context — flag for CLAUDE.md update:
- User stories or ADRs proposed by agents are missing edge cases
- Code review repeatedly catches the same domain-knowledge gap
- An agent makes a wrong architectural decision due to missing app context
- A new feature adds entities, state machines, or business rules not yet documented

## Exceptions (do NOT delegate)
- `.claude/settings.json` / `.claude/settings.local.json` (settings, not content)
- `.claude/hooks/` scripts (operational)
- `.claude/agent-memory/` files (transient, per-session)
