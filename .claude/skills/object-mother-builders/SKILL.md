---
name: object-mother-builders
description: Fluent Mother and builder classes shared as test artifacts. Use when tests need domain fixtures.
---
# Object-mother test-data builders

> **Generic "how" only.** No concrete entity/module names in the body — those live in the code-map.

## When to use
Building domain objects for tests without repeating constructor noise: a default-valid instance you can
tweak per test, reused across modules.

## How
- One `Mother` per domain type with static factories returning a **valid default**; expose a fluent
  builder (`with…` methods) so a test overrides only the field it cares about.
- Keep mothers in `src/test/java`; publish them as **test artifacts** so other modules reuse them
  instead of copy-pasting fixtures.
- Make defaults realistic and invariant-satisfying (so a mother never produces an illegal object);
  randomize nothing that a test asserts on.
- Name builders for intent (`aValid…`, `an…Without…`) so tests read as scenarios.

## Pattern signals (discovery cues)
Classes named `*Mother` / `*TestData` with static factory methods + an inner fluent `*Builder`; a
test-jar/test-fixtures producer convention; `testImplementation(... "testArtifacts")` style consumption.

## Project specifics → see docs
- Code map (mother exemplars, the test-artifact convention) → `docs/code-maps/object-mother-builders.md` *(per-repo map, written by the pattern-scanner — resolves once harvested)*

## Guardrails (what NOT to do)
- Don't duplicate fixtures per module — share the mother as a test artifact.
- Don't bake random values a test then asserts on.
- Don't let a mother emit an invalid object — defaults must satisfy invariants.

## Definition of done
- [ ] A `Mother` + fluent builder per heavily-used type; valid defaults; shared via test artifacts; tests override only what matters.
