---
globs:
  - "**/*.py"
---

# Clean Code Standards

## Hard Limits
- **50 lines** per function/method — beyond this, functions have multiple responsibilities and become hard to test in isolation
- **3 arguments** max — group related params into a DTO or dataclass
- **3 indentation levels** max — deeper nesting signals logic that should be extracted
- **10 lines** per if/else/try/except/while/for block
- **200 lines** per file (target), **500 lines** hard limit
- **No flag arguments** — split into separate functions instead

## Naming Conventions (Project-Specific)
- Interactors: `<Action><Entity>Interactor` (e.g., `CalculateScoreInteractor`)
- DTOs: always suffix `DTO` (e.g., `PaymentDetailsDTO`)
- Storage methods: `get_*`, `create_*`, `update_*`, `delete_*`, `get_*_bulk`
- DTO converters in storage: `_prep_*_dto()` or `_prepare_*_dto()`
- Exceptions: descriptive condition using domain language from user stories (e.g., `CalculatedTDRAreaIsLessThanScrutinyTDRArea`, not a developer-invented synonym)
- **No single-character or cryptic variable names** — every variable name describes what it holds. Use `fee_rule_set` not `frs`, `order_index` not `i`, `field_response` not `r`. The only exception is conventional loop counters in trivial comprehensions (`[x.id for x in items]`)
- **Names describe side-effects — both directions** — a method name must reflect the side effects it HAS and must not imply one it lacks. If it writes, say so: `create_or_get_session()` not `get_session()` when it creates. If it only READS, use a read verb (`get_` / `read_` / `fetch_`) — never a construction/capture/write verb for a pure read. WRONG `snapshot_publish_state(...)` / `build_...` / `capture_...` / `compute_...` when the body only fetches (reads as "writes a snapshot") → RIGHT `get_publish_state(...)`. (Real case: a pure-read `_snapshot_publish_state_by_rule_id` renamed to `_get_publish_state_by_rule_id`.)
- **No metaphor nouns — name the thing, not a picture of it.** A name must carry domain or mechanical meaning on its own. Reject a noun whose meaning only exists in the head of whoever coined it (`footprint`, `fingerprint`, `envelope`, `bucket` when it isn't the domain's bucket), and reject a word already loaded with another meaning in this stack (`snapshot` — a DB/VCS term and a pytest fixture name here; `context`, `state`, `manifest` when they mean something narrower). WRONG `append_footprint: Dict[str, List[str]]` → RIGHT `item_ids_by_allocation_group_set_id`. WRONG `RecordedBucketResolver` → RIGHT a name that says what it answers: `FindCurrentBucketForRecordedId`. Test: can a reader who has never read the ADR say what the name holds or does? If the answer needs the design doc, the name failed. *(Real case: the user bounced `snapshot`, `footprint`, and `RecordedBucketResolver` in one review — "did not understand the purpose from the name itself".)*
- **Domain terminology is canonical** — variable names, exception names, and DTO fields use the exact terms from user stories / acceptance criteria. Do not invent synonyms (e.g., if the story says `calculated_tdr_area`, do not rename to `total_cost_value`)
- **Do not conflate similar-sounding domain terms** — `field_ref_id` is not `field_id`, `entity_fee_rule_set` is not `fee_rule_set`, `order_contributed_entity` is not `order_entity`. When a term has a prefix or suffix, it means something different. Read the model/DTO definition to confirm the exact field name before using it
- **Distinguish method names from domain concepts** — API/service/storage method names describe the operation they perform; domain variable names describe what the result represents. Renaming a domain concept does NOT mean renaming the method that computes it

## Control Flow
- **Positive conditionals** — `if should_process()` not `if not should_skip()`
- **Extract complex conditions** into descriptively named functions
- **Encapsulate boundary conditions** with named constants
- **`is not None` over truthiness** — use `if value is not None` when `0`, `""`, or `[]` are valid values. Never use `if value` for presence checks in validation logic
- **Type-safe operations** — guard `.strip()`, `.lower()`, etc. with `isinstance(value, str)` when the value might not be a string

## Constants & Variables
- **No magic numbers/strings** — use named constants
- **Use explanatory variables** for complex expressions
- **Enum values**: always access with `.value` (`TransactionEntityType.PIPELINE_ITEM.value`)
- **Enum `.value` before an ORM filter** — when filtering a Django CharField by an enum, pass `enum_member.value`, never the bare member. A `BaseEnumClass` member compares unequal to the stored string, so `.filter(status=MyEnum.ACTIVE)` silently matches nothing while `.filter(status=MyEnum.ACTIVE.value)` works. Sharpest at adapter boundaries where a member flows from domain code into a queryset (real bug: a PMU rule-set export returned nothing because members reached `.filter()`; a sibling decider passed only because it happened to use strings).

## Business Logic
- **Never assume formulas** — if a business formula is not explicitly stated in user stories or acceptance criteria, ASK the user before implementing. Never derive or guess mathematical relationships between domain values.
- **General-purpose solutions** — implement the actual logic that solves the problem, not solutions that only work for specific test inputs. Do not hard-code values to make tests pass. Tests verify correctness — they do not define the solution. If a test appears incorrect, flag it rather than working around it.

## DRY Enforcement
- **Wire utilities immediately** — when creating a shared utility, replace ALL existing copy-pasted occurrences in the same PR. Never create a utility without wiring it in.
- **Scan before committing** — search for duplicate code blocks across the changeset, especially in plugin files, webhook handlers, and similar-shaped modules.
- **Consistent DTO attributes** — if all DTOs in a module use `frozen=True`, new DTOs must too.

## Required Practices
- **Type hints** on ALL parameters and return types — use `Optional`, `List`, `Dict`, specific types
- **No storage calls inside loops** — fetch data once, process in memory. N+1 queries are the #1 performance issue in this codebase
- **No logging in business logic** — no `print()`, `logger.info()`, or any stdout/stderr output. Logging belongs in adapters and presenters, not domain logic *(hook-enforced: `quality-gate.sh` catches print/logger in interactors)*
- Apply **Law of Demeter** — limit object chain calls
- **Pass a callee only the data it reads (method-level ISP)** — when a method uses only one derived slice of a value, pass that slice, not the whole DTO/dict. A parameter the callee only partially reads hides the real dependency and over-couples; the caller should derive the narrow value. WRONG `_build_removal_plan(officer, publish_state_by_rule_id)` when the body reads only the exec-config ids from that map → RIGHT `_build_removal_plan(officer, exec_config_ids)` with the caller deriving the ids.
- **Comments and docstrings** — see the Comments section below. Default is NONE.
- **Top-level imports** — import constants and enums at module top, not inside methods (lazy imports only for circular dependency avoidance)

## Comments — the design record does not live in source

### WHY
This was one clause inside the docstring bullet above, and every file of a freshly-built feature
violated it (2026-08-11 review: seven `#TODO: never add these type of comments` on one feature,
escalating in irritation). The clause failed because its exception — "behavior is non-obvious" —
is exactly how a design-rationale comment self-certifies. An agent that has just read the ADR is
holding the rationale in working context and, with no instruction to withhold it, pastes it into
the source. **The design record has a home, and source files are not it.**

### The rule
**WHY goes in the ADR. WHAT goes in the name. The source file gets neither.**

Delete, do not write:
- **Rationale prose** — why this shape was chosen, what it was chosen over, what invariant it upholds. That is the ADR's Decisions section, where a reader can actually find it and where it stays current.
- **Citations in source** — `ADR-001 D4a`, `US-7 AC1`, `§ Behaviour step 7` in a `.py` file. A positional citation rots silently (`references/plain-language.md`), and the reader who needs it is reading the ADR, not this line. *(Tests are the exception — see Still legal.)*
- **Restatement** — a comment or docstring that says what the next lines already say. `# Fetches every id in one query, appends in memory, one bulk_update` above a method that does exactly that is noise.
- **Contract narration on a DTO or an abstract method** — a dataclass explaining its own serialization, an `@abc.abstractmethod` body describing how an implementation should behave. The field names and the type hints are the contract; the implementation note belongs to whoever implements it, not to the interface.
- **"Known limitations" notes** — those are backlog items. File them in the backlog doc and link nothing.

### Still legal (do not over-correct into "no comments ever")
- **A non-obvious mechanical fact the code genuinely cannot state** — an ordering dependency, an
  external-API quirk, a deliberate-looking-wrong line. One or two lines, stating the FACT, not the
  history: `# storage returns most-recent-first` beats six lines about which user story decided it.
- **Public API consumed by other apps** — `app_interfaces/` and base classes may carry a docstring
  describing the contract for an external caller.
- **AC-traceability labels in TESTS** — `# Arrange — US-12 AC3: an empty plan is not an error` is
  encouraged; a test's job is to name the acceptance criterion it proves. This rule is about
  production source only.

### The reflex
Before writing a comment, ask: *is this fact, or is this the story of how we decided?* Story →
the ADR. Fact the code can carry → rename the variable or extract the method. Fact the code
cannot carry → one line, no citation. When it's genuinely a toss-up, leave it out: a missing
comment costs one read of the ADR; a wrong one costs trust in every comment in the file.

*(Hook-enforced, partially: `quality-gate.sh` flags `ADR-`/`US-` citations in non-test `.py`
files. The rest is authoring-time judgement — the reviewer and `/self-review-checklist` carry it.)*
