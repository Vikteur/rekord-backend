---
paths:
  - "**/adapter/**"
  - "**/*-adapter/**"
---
# Adapter layer — always-on guardrails

> **Backstop, not a knowledge store.** Always-on for any edit in an adapter package or a `*-adapter`
> module — keep tiny and **project-noun-free**. **Hard cap: ≤5 invariant lines**; depth →
> `api-first-controller` / `persistence-repository` skills (lazy), facts →
> `docs/code-maps/api-first-controller.md`. Outbound integration code lives in its own layer — see
> the gateway instructions. Do not restate skill steps here. See `ARCHITECTURE.md` §2 (caution), §3
> (blueprint repo).

- Controllers are thin: map contract ↔ usecase, no business logic.
- Controllers are generated from the contract (api-first); do not hand-edit generated types.
- A repository implementation here satisfies a usecase-owned port; it never widens it.
- No domain invariants here — push them into the domain.
