---
globs:
  - "workflow_engine/**"
---

# Rich Domain Model — Scoped Exception (workflow_engine)

## WHY this exception exists
`clean-architecture.md` mandates anemic DTOs ("pure data, no methods") because business logic scattered across DTOs is untestable and leaks framework concerns. An *engine* inverts that economics: its entire value is domain behavior (gate evaluation, transition logic), and forcing that behavior out of the domain objects into service functions scatters the engine's logic — exactly the OCP-hostile shape the engine exists to eliminate. Locked at REF-001 design (bounded Option A).

## The Rule — inside `workflow_engine/` only
- **Domain entities carry behavior.** The aggregate root (`Transition`) and engine-anchored entities (`Guard`, `TransitionLogic`, gate/engine objects) hold their own domain methods (e.g., `evaluate`, `resolve_destination`). Plain Python objects — behavior + state together.
- **Reconstitution happens at the gateway** (anti-corruption layer). Storage rows and config blobs are parsed into rich domain objects at the engine's boundary; inside the engine, only rich objects circulate.
- **Boundary DTOs stay anemic.** Anything crossing the app boundary — port results, GraphQL payloads, `TransitionFacts` — is a pure-data `@dataclass` per the global rule. Rich objects never leak out of the engine.
- **No framework in domain objects.** No Django imports, no ORM instances, no request objects — the engine's domain layer stays framework-free (this part of `clean-architecture.md` is NOT relaxed).

## Bounds (what this does NOT license)
- Other apps do not get rich DTOs — this exception is path-scoped here for a reason.
- Rich objects are not models: persistence stays in storages; domain objects are reconstituted, never saved directly.
- A method on a domain object must be *that entity's own behavior*. Cross-entity orchestration still belongs to interactors/engines, not to a god-object aggregate.

Reviewer note: inside `workflow_engine/`, behavior-carrying domain classes are intentional — do not flag them as DTO violations. Flag the opposite: rich objects escaping across the app boundary.
