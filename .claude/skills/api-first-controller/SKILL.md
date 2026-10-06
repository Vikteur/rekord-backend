---
name: api-first-controller
description: Thin controller implementing an OpenAPI-generated Api interface. Use for contract-first REST.
---
# API-first controller

> **Generic "how" only.** No concrete controller/tag/package names in the body — those live in the code-map.

## When to use
Building a REST endpoint in a contract-first project where the controller interface + DTOs are
**generated** from an OpenAPI spec at build time.

## How
- Implement the generated `*Api` interface; keep the controller **thin** — validate inputs, call one
  use-case, map domain → generated DTO, return. No business logic here.
- Never hand-edit generated sources; if the shape is wrong, change the **spec** and regenerate.
- Map domain↔DTO in a dedicated mapper (testable in isolation), not inline.
- Let exceptions propagate to the central error handler ([[exception-to-http]]); don't catch-and-swallow.
- Inject the use-case via the constructor; the controller depends inward, never on another adapter.

## Pattern signals (discovery cues)
Controllers `implements <Name>Api` where `*Api` is under a generated source set; an OpenAPI codegen
plugin wired into the build; DTOs from a generated `model` package; a sibling `*DomainToDTOMapper`.

## Project specifics → see docs
- Code map (codegen plugin, tag→controller exemplars, mapper convention) → `docs/code-maps/api-first-controller.md` *(per-repo map, written by the pattern-scanner — resolves once harvested)*

## Guardrails (what NOT to do)
- Don't put business logic or persistence in the controller — delegate to the use-case.
- Don't hand-edit generated interfaces/DTOs — edit the contract.
- Don't map domain→DTO inline — use a tested mapper.

## Definition of done
- [ ] Controller implements the generated interface, delegates to one use-case, maps via a tested mapper, errors flow to the central handler.
