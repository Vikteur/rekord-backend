---
paths:
  - "**/usecase/**"
  - "**/*-usecase/**"
---
# Usecase layer — always-on guardrails

> **Backstop, not a knowledge store.** Always-on for any edit in a usecase package or a `*-usecase`
> module — keep tiny and **project-noun-free**. **Hard cap: ≤5 invariant lines**; depth →
> `usecase-orchestration` skill (lazy), facts → `docs/code-maps/usecase-orchestration.md`. Do not
> restate skill steps here. See `ARCHITECTURE.md` §2 (caution) and §3 (blueprint repo).

- Usecases orchestrate domain + ports; they hold application logic, not domain invariants.
- Depend on domain and on port interfaces only — never on adapter implementations.
- A repository interface here is a **port**: it is owned by this layer and names domain types only.
- Transaction boundaries live here, not in the controller or the gateway.
- No HTTP / serialization concerns in a usecase.
