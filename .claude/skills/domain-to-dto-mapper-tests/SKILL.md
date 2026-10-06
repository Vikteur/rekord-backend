---
name: domain-to-dto-mapper-tests
description: Parameterized mapper tests fed by object-mothers, asserting field by field. Use when testing a layer mapper.
---
# Domain-to-DTO mapper tests

> **Generic "how" only.** No concrete mapper/DTO names in the body — those live in the code-map.

## When to use
Verifying a mapper that converts a domain object to a transport DTO (or back): every field carried,
nulls/optionals/collections handled, enums translated.

## How
- Drive inputs from object-mothers ([[object-mother-builders]]); assert the DTO **field by field**, not
  by a serialized blob, so a wrong/dropped field is obvious.
- Use `@ParameterizedTest` for the variants (empty collections, absent optionals, each enum value).
- Cover the round-trip if a reverse mapper exists (domain → DTO → domain is stable).
- Keep the mapper pure (no I/O); the test needs no Spring context.

## Pattern signals (discovery cues)
Test classes named `*DomainToDTOMapperTest` / `*MapperTest`; `@ParameterizedTest` + `@MethodSource`;
inputs from `*Mother`; per-field `assertThat(dto.getX()).isEqualTo(...)`.

## Project specifics → see docs
- Code map (mapper exemplars, parameterization style) → `docs/code-maps/domain-to-dto-mapper-tests.md` *(per-repo map, written by the pattern-scanner — resolves once harvested)*

## Guardrails (what NOT to do)
- Don't assert on a whole serialized JSON string — assert fields.
- Don't skip the null/empty/enum edge cases — that's where mappers break.
- Don't boot Spring for a pure mapper test.

## Definition of done
- [ ] Field-by-field assertions, parameterized edge cases, mother-fed inputs, no Spring context; reverse round-trip covered if applicable.
