---
paths:
  - "**/domain/**"
  - "**/*-domain/**"
---
# Domain layer — always-on guardrails

> **Backstop, not a knowledge store.** Always-on for any edit in a domain package or a `*-domain`
> module, so keep this tiny and **project-noun-free**. **Hard cap: ≤5 invariant lines** — anything
> procedural belongs in the `domain-modeling` skill body (lazy), project facts in
> `docs/code-maps/domain-modeling.md`. Do not restate skill steps here (that would be always-on
> duplication). See `ARCHITECTURE.md` §2 (caution) and §3 (blueprint repo).

- No framework imports in `domain` (no Spring, no JPA, no web, no I/O).
- Invariants enforced in constructors / factory methods; no setters that can break them.
- Domain events are published from the domain, not the adapter.
- The domain depends on nothing outward (dependency direction points in).
