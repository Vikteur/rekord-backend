---
name: jvm-testing
description: JVM tests as behavior specs — Given-When-Then, JUnit 5 and AssertJ. Use when writing or reviewing tests.
---
# JVM testing
> **Generic "how" only.** Zero project nouns (no package roots, module names, tag names, fixture classes). Link a docs leaf for any project fact. See `ARCHITECTURE.md` §1 (blueprint repo).
>
> Absorbs the former `junit-tests` skill — one skill for JVM test discipline plus its JUnit 5 idiom.

## When to use
Writing or reviewing any test on the JVM: red tests before implementation, unit tests for a class's
behavior, or when deciding what to mock, how to name a test, and where a slow test belongs. The
test-writer's default; developers use it to keep tests green and meaningful.

## How
- **Given-When-Then** — three visible phases per test; establish state, invoke one action, assert the outcome. No logic branches in the test body.
- **One behavior per test** — a single reason to fail. A second assertion group means a second test.
- **Name the test as a behavior spec** — read it as a sentence about *what the unit does*, not the method called (`returns_empty_when_no_match`, not `testFind`).
- **Mock at ports/boundaries only** — stub the collaborators the unit *owns as dependencies* (gateways, repositories, clocks); never mock internal helpers or value objects. Prefer real objects where cheap.
- **Assert on outcomes, not implementation** — check returned values and observable state; prefer fluent assertions (AssertJ) for clarity; avoid `verify` on internal call order unless the interaction *is* the contract.
- **Parameterize repetitive cases** (`@ParameterizedTest`) instead of copy-pasting near-identical tests.
- **Make tests deterministic** — no real clock/network/random; inject and fix them. Cover edge cases and failure paths, not just the happy path.
- **Keep units fast and context-free** — no framework boot, no container, no I/O. A unit test is plain construction + call.
- **Split the slow set** — anything needing a framework context, DB, or network is an integration test in a separate, separately-run set — not mixed with units. That set is where [[spring-boot-slice-tests]] and [[testcontainers]] apply.

## Pattern signals (discovery cues — how the scanner recognizes this in any codebase)
- A test source tree mirroring `src/main`; `@Test`/`@ParameterizedTest`/`@Nested` (JUnit 5 `org.junit.jupiter`).
- AssertJ (`assertThat`) / Mockito on the test classpath; `*Test` / `*IT` naming conventions.
- Test names in behavior form; `given/when/then` or `// arrange` comments; fixture builders or shared base test classes.
- A separate slow/integration set (distinct source set, suffix, or tag) with its own build task.

## Project specifics → see docs
- Code map (test layout, helpers/fixtures, naming, exemplars, generated) → `docs/code-maps/jvm-testing.md` *(per-repo map, written by the pattern-scanner — resolves once harvested)*

## Guardrails (what NOT to do)
- Don't mock internal collaborators or the class under test — mock only its owned ports.
- Don't assert on implementation detail (call counts, private state) when an outcome assertion would do.
- Don't pack multiple behaviors into one test, or branch/loop inside a test body.
- Don't write order-dependent or time/network-dependent tests.
- Don't boot a framework context or touch I/O in a unit test — that belongs in the integration set.

## Definition of done
- [ ] Each test is one behavior, GWT-structured, named as a behavior spec.
- [ ] Mocks sit at ports/boundaries; assertions target outcomes, not internals; repetitive cases parameterized.
- [ ] Tests deterministic; edge and failure paths covered; units run with no framework boot or I/O; slow tests live in the separate set.
