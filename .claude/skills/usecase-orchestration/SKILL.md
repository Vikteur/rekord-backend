---
name: usecase-orchestration
description: Transactional use-case over domain and ports, free of web and persistence types. Use for the use-case layer.
---
# Use-case orchestration

> **Generic "how" only.** No concrete use-case/repository names in the body — those live in the code-map.

## When to use
Implementing application logic that coordinates domain objects and repository ports for one business
operation — the layer between controllers and the domain.

## How
- One use-case = one operation. It takes a **request object**, calls domain + repository **ports**, and
  returns a **response object** (or domain type) — never a web DTO or a persistence entity.
- Own the **transaction boundary** here (`@Transactional` at the use-case), not in the controller or
  repository. Keep the transaction tight.
- Depend on **interfaces** (repository/gateway ports) defined in this/the inner layer; the adapter
  provides the implementations.
- Put business rules/invariants in the **domain**; the use-case orchestrates, it doesn't reimplement them.
- Validate the request up front; surface failures as typed domain/application exceptions.

## Pattern signals (discovery cues)
Classes named `*UseCase`/`*Service` in a use-case module with `@Transactional`; constructor-injected
repository/gateway interfaces; request/response value objects; no web/JPA imports.

## Project specifics → see docs
- Code map (use-case exemplars, transaction + port conventions) → `docs/code-maps/usecase-orchestration.md` *(per-repo map, written by the pattern-scanner — resolves once harvested)*

## Guardrails (what NOT to do)
- Don't accept/return web DTOs or persistence entities — use request/response + domain types.
- Don't put the transaction boundary in the controller or repository.
- Don't reimplement domain invariants in the use-case — delegate to the domain.

## Definition of done
- [ ] One operation per use-case; transaction owned here; depends on ports; request/response objects; rules live in the domain; a test drives it with mocked ports.
