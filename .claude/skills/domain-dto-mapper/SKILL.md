---
name: domain-dto-mapper
description: A pure, field-explicit mapper between domain and transport DTO. Use when a controller or gateway crosses that edge.
---
# Domain-to-DTO mapper

> **Generic "how" only.** No concrete mapper/DTO names in the body — those live in the code-map.

## When to use
Crossing the boundary between a domain object and a generated/transport DTO — in a controller
(domain → response DTO) or a gateway (wire DTO → domain).

## How
- Put the conversion in a **dedicated mapper** (a class or static methods), not inline in the
  controller/gateway. Keep it **pure** (no I/O, no Spring) so it's unit-testable in isolation.
- Map **field by field, explicitly**; handle nulls/optionals/collections deliberately; translate enums.
- Keep direction clear (separate `toDto` / `toDomain`); if both exist, make the round-trip stable.
- Don't put business logic in the mapper — it only restructures data.
- Pair it with a mapper test ([[domain-to-dto-mapper-tests]]).

## Pattern signals (discovery cues)
Classes named `*DomainToDTOMapper` / `*Mapper` in the adapter layer with `toDto`/`toDomain`-style
methods; no framework/IO deps; a sibling `*MapperTest`.

## Project specifics → see docs
- Code map (mapper exemplars, hand-coded vs generated DTOs) → `docs/code-maps/domain-dto-mapper.md` *(per-repo map, written by the pattern-scanner — resolves once harvested)*

## Guardrails (what NOT to do)
- Don't map inline in controllers/gateways — use the dedicated mapper.
- Don't put business rules or I/O in a mapper.
- Don't silently drop fields — map explicitly, cover edges in the test.

## Definition of done
- [ ] Pure dedicated mapper, explicit field mapping, edges handled, no business logic; a mapper test asserts each field + round-trip where applicable.
