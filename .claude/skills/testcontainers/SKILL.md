---
name: testcontainers
description: Integration-test against real backing services with Testcontainers. Use instead of in-memory fakes.
---
# Testcontainers

> **Generic "how" only.** Zero project nouns. Image tags, init scripts, base classes and the
> module's migration location live in the code-map docs leaf, referenced below. See `ARCHITECTURE.md` §1 (blueprint repo).
>
> Merges the former `testcontainers-postgres` and `testcontainers-services` skills — one mechanism,
> two service flavors.

## When to use
Integration tests that must exercise a real service instead of a substitute: repository/persistence
tests that need true SQL behavior (vendor types, DDL, constraints, migrations, dialects) where an
in-memory database would lie — or adapters that talk to a real backing service over the network (a
search/index engine, an SMTP server, a cache, a message broker) where a mock would not exercise the
real protocol, serialization, or readiness behavior.

## How — the shared mechanism
- Start the service in a container from a **pinned image** (never a floating tag); reuse **one
  static container per JVM** so it starts once, not per test.
- Wire the container into Spring with an `ApplicationContextInitializer`: start it, then push its
  coordinates via `TestPropertyValues` onto the environment. Register the initializer(s) with
  `@ContextConfiguration(initializers = …)` on a shared base test class; one initializer per service.
- Keep tests independent: each test sets up and asserts its own data; never depend on order.

## Database flavor (Postgres and friends)
- Let the real **migration tool** build the schema ([[flyway-migrations]] — enable it for the test
  profile) so tests run the same DDL as production — never hand-build the schema in test code.
- Disable the framework's embedded-database swap (`replace = NONE`) so the container datasource wins.
- Seed only what every test needs via a classpath init script mounted into the container; keep
  per-test data in builders/mothers ([[object-mother-builders]]), not global fixtures.

## Service flavor (search, mail, cache, queue, …)
- Model each service as a `GenericContainer` with declared exposed ports and env vars.
- Use a **wait strategy** so the container is only "started" once actually ready — an HTTP health
  endpoint or log/port readiness probe, never a blind sleep.
- After start, read the dynamically mapped host+port (`getHost()`, `getMappedPort(...)`) and inject
  them as properties; never hardcode the published port. When a bean needs live coordinates (e.g. a
  mail sender), build it from the container's mapped host/port inside the test configuration.

## Pattern signals (discovery cues — how the scanner recognizes this in any codebase)
- `org.testcontainers.*`: `PostgreSQLContainer`, `GenericContainer<>(DockerImageName.parse(...))`
  with `.withExposedPorts(...)` / `.withEnv(...)` in `src/test/java/**`.
- `ApplicationContextInitializer` + `TestPropertyValues` setting datasource/service properties;
  initializers composed via `@ContextConfiguration(initializers = {...})` on a shared base class.
- `@DataJpaTest`/`@SpringBootTest` with `@AutoConfigureTestDatabase(replace = NONE)`; a migration
  tool enabled for tests; `.waitingFor(Wait.forHttp(...))` readiness probes.

## Project specifics → see docs
- Code map (which services, images, initializer/base classes, migration location, init scripts, exemplars) → `docs/code-maps/testcontainers.md` *(per-repo map, written by the pattern-scanner — resolves once harvested)*

## Guardrails (what NOT to do)
- Don't test repositories against an in-memory DB when production is Postgres — behavior diverges.
  The slice this container serves is [[spring-boot-slice-tests]]'s `@DataJpaTest`.
- Don't start a fresh container per test method; share one static instance per JVM.
- Don't hand-build the schema in test code when a migration tool already owns it, and don't leave
  the embedded-database replacement on — it shadows the container datasource.
- Don't hardcode published ports or rely on `Thread.sleep` — mapped ports + a real wait strategy.
- Don't pin to a floating tag (`latest`) — fix the image version for reproducibility.

## Definition of done
- [ ] Each service runs as a pinned container, one static instance per JVM, wired via initializer(s)
      on a shared base; no hardcoded ports; real readiness waits.
- [ ] Database tests run schema built by the migration tool with the embedded swap disabled.
- [ ] Tests are independent and deterministic.
