# Interactive Questions

Applies to the main session and every subagent. Governs HOW you ask the user a question once `consent-granularity.md` has decided you should.

## Use `AskUserQuestion` when the answer is enumerable

- Approval gates (PRD, ADR, plan, commit, push)
- Scope clarifications with a discrete option set
- Design trade-offs between named alternatives
- The env-promote checklist (alpha / beta / gamma / tg-bn-gamma / tg-bn-uat — `multiSelect: true`)
- Any yes/no confirmation

The user gets a clickable picker — faster, less typo-prone, structured for telemetry. List the recommended option FIRST with " (Recommended)" appended to its label.

## Use plain text when the answer is open-ended

- Free-form prose (writing user stories, describing a bug)
- Brainstorming and design discussion
- Anything where 2-4 fixed options would distort the answer

## Hard rules

- Never ask a yes/no in plain text — use `AskUserQuestion`.
- Never enumerate N options in plain text and ask the user to pick — use `AskUserQuestion`.
- Batch unrelated questions into ONE call (max 4 questions per call, 2-4 options each). See `agent-interaction.md` on batching.
- Do NOT add an "Other" option manually — the harness auto-appends it for free-form fallback.
- Decide WHETHER to ask using `consent-granularity.md` (announce-and-execute defaults beat questions). This rule only governs HOW.
- **Ground the question before firing the picker.** A picker is a conclusion, not a discovery tool — do the grounding read (the code/config/consumers the options describe) FIRST, so the options are real, correct, and complete. Firing `AskUserQuestion` before you've read enough offers wrong or missing options and the user has to bounce it. If you can't yet name the true option set, ask an open plain-text clarifying question instead, then enumerate once grounded.

## Tool loading

`AskUserQuestion` is a deferred tool. Load it on-demand right before you need it:
`ToolSearch` with query `select:AskUserQuestion`. Don't pre-load it speculatively.