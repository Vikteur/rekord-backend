---
name: spring-boot-slice-tests
description: Spring Boot slice tests for the web and persistence adapters, collaborators mocked. Use for adapter tests.
---
# Spring Boot slice tests

> **Generic "how" only.** No concrete controller/entity names in the body — those live in the code-map leaf.

## When to use
Testing adapter-layer code with the smallest Spring context that exercises it: a controller's
request/response/validation/error mapping, or a repository's queries/mappings — without booting the
whole application.

## How
- **Controllers**: `@WebMvcTest(TheController.class)` + `MockMvc`; mock the use-case collaborators
  (`@MockitoBean`); assert status, body and error mapping. Don't load the full context. A slice that
  makes a real outbound HTTP call stubs it with [[wiremock-gateway-stubs]].
- **Repositories**: `@DataJpaTest` against a real database via a container ([[testcontainers]], so
  dialect/migrations are exercised), not an in-memory substitute when the prod DB differs.
- Share setup through an abstract base test per slice (`AbstractControllerTest` / `AbstractRepositoryTest`)
  so config (security test setup, cache manager, container) is declared once.
- Build inputs with object-mother/builders ([[object-mother-builders]]); keep each test one behavior,
  named `given…_when…_then…` — the discipline is [[jvm-testing]]'s, a slice test does not relax it.

## Pattern signals (discovery cues)
`@WebMvcTest` / `@DataJpaTest` annotations; `MockMvc.perform(...)`; `@MockitoBean`; abstract `*ControllerTest`
/ `*RepositoryTest` base classes; testcontainers for the DB; `given_when_then` method names.

## Project specifics → see docs
- Code map (base test classes, container setup, exemplars) → `docs/code-maps/spring-boot-slice-tests.md` *(per-repo map, written by the pattern-scanner — resolves once harvested)*

## Guardrails (what NOT to do)
- Don't use `@SpringBootTest` for a single controller/repo — that's the wrong (heavy) slice.
- Don't mock the repository under test in a `@DataJpaTest` — exercise the real query.
- Don't assert on full JSON blobs where a targeted field/status assertion is clearer.

## Definition of done
- [ ] The slice annotation matches the unit under test; collaborators mocked (controller) or DB real (repo);
  base test reused; mothers for inputs; behaviors are red before the production code makes them green.
