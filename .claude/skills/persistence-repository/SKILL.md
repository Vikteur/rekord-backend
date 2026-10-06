---
name: persistence-repository
description: Implement a repository port as a JPA-backed adapter, keeping JPA out of inner layers. Use when persisting state.
---
# Persistence repository (adapter)

> **Generic "how" only.** No concrete repository/entity names in the body — those live in the code-map.

## When to use
Backing a use-case's repository **port** (interface in the inner layer) with a real datastore — the
adapter that turns domain aggregates into rows and back.

## How
- The **port** (interface) lives in the use-case/inner layer; the adapter class **implements** it
  (often a thin `Default<X>Repository` delegating to a Spring Data interface).
- Map **domain ↔ JPA entity** at this edge; the domain never sees `@Entity` types and the entity never
  leaks outward.
- Keep queries in the Spring Data interface / explicit query methods; keep transactions owned by the
  **use-case** ([[usecase-orchestration]]), not the repository.
- Return domain types (or `Optional<domain>`); translate persistence exceptions to typed errors.
- Cover it with a real-database slice test ([[spring-boot-slice-tests]] / [[testcontainers]]).

## Pattern signals (discovery cues)
A use-case-layer `*Repository` interface implemented by an adapter `Default*Repository` (`@Repository`);
a sibling Spring Data `JpaRepository`/`CrudRepository`; domain↔entity mapping at the boundary.

## Project specifics → see docs
- Code map (port↔impl pairs, entity mapping, query conventions) → `docs/code-maps/persistence-repository.md` *(per-repo map, written by the pattern-scanner — resolves once harvested)*

## Guardrails (what NOT to do)
- Don't let `@Entity` / JPA types cross into domain or use-case code.
- Don't own the transaction in the repository — the use-case does.
- Don't return entities to callers — return domain types.

## Definition of done
- [ ] Port in the inner layer, `@Repository` adapter implements it; domain↔entity mapped at the edge; returns domain types; a Testcontainers slice test covers a query.
