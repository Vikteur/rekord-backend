---
name: test-architecture-analysis
description: Map test frameworks, layout, types, and coverage discipline. Use when onboarding to wire testing skills.
---
# Test-architecture analysis

> **Generic "how" only.** Zero project nouns. The concrete runners, test dirs, and conventions you
> find are written to the inventory / testing code-map, referenced below. See `ARCHITECTURE.md` §1 (blueprint repo).

## When to use
On onboarding — when you need to know *how this project tests itself* to record the testing architecture
and decide which testing skills the layers should carry.

## How
- **Identify the test frameworks and runners** per side from the dev dependencies and config files
  (the runner, the assertion lib, the mocking lib, the coverage tool).
- **Map the test layout**: where tests live relative to source (co-located vs mirrored tree), the file
  naming shape, and how each test *type* is separated (unit, integration, e2e, contract, arch-fitness).
- **Characterise the discipline**: is there a TDD/red-green convention, a coverage threshold, required
  arch-fitness rules, fixture/builder patterns, and how external I/O is faked (mock vs stub vs container).
- **Note the seams to infra**: in-memory vs real datastore, HTTP mocking, test-container usage.
- **Surface candidate testing skills** the project would wire (per layer/type) for the skill-harvest pass.
- Cite a representative test file and the config path for each finding.

## Pattern signals (discovery cues — how the scanner recognizes this in any codebase)
- Runner/config files: `jest.config.*`, `vitest.config.*`, `karma.conf.*`, `pytest.ini`/`tox.ini`,
  `*Test.java`/`*IT.java`, `surefire`/`failsafe` config, `playwright.config.*`, `cypress.config.*`.
- Test directories (`test/`, `tests/`, `__tests__/`, `spec/`, `src/test/`) and naming suffixes
  (`*.spec.*`, `*.test.*`, `*Test`, `*IT`).
- Mocking/fixture markers, coverage config, and architecture-fitness test classes.

## Project specifics → see docs
- The discovered facts (with provenance) → `docs/_inventory/40-test-architecture-analyst.md`
- The testing code-map it seeds → `docs/code-maps/README.md`

## Guardrails (what NOT to do)
- Don't equate "has tests" with a discipline — state what's enforced (thresholds, gates) vs incidental.
- Don't enumerate every test file; sample representative ones and count with a script.
- Keep concrete dirs/runner names out of this skill body — they live in the inventory / code-map leaf.

## Definition of done
- [ ] Frameworks, runners, and coverage tooling identified per side, each sourced to config.
- [ ] Test layout, naming, and the separation of test types mapped.
- [ ] Discipline (TDD, thresholds, arch-fitness, faking strategy) characterised; testing-skill candidates listed.
