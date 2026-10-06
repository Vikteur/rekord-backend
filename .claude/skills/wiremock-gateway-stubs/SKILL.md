---
name: wiremock-gateway-stubs
description: Stub outbound HTTP in tests with WireMock and assert requests. Use when testing a gateway against a fake.
---
# WireMock gateway stubs

> **Generic "how" only.** No endpoints, service names, or fixtures in the body — those live in the code-map.

## When to use
Testing a gateway/HTTP client ([[gateway-client-hygiene]]) without the real remote: drive happy-path,
error, timeout and malformed responses deterministically, and assert the request the client actually
sent. The test discipline around it is [[jvm-testing]]'s.

## How
- Register a `WireMockExtension` (JUnit 5) with a dynamic port; point the client's base URL at it.
- `stubFor(...)` the responses per scenario (status, body, headers, delay for timeouts); keep one stub
  per behavior under test.
- Assert outbound requests with `verify(...)` / request matchers — confirm path, method, headers, body.
- Cover failure modes (5xx, connection reset, slow) so the [[resilience4j]] circuit breaker, retry and
  fallback paths are actually exercised, not just declared.
- Reset stubs between tests; don't share mutable stub state.

## Pattern signals (discovery cues)
`com.github.tomakehurst`/`org.wiremock` deps; `@RegisterExtension WireMockExtension`; `stubFor`/`verify`;
client base-URL pointed at `wireMock.baseUrl()` / a dynamic port in `src/test/java/**`.

## Project specifics → see docs
- Code map (which gateways are stubbed, fixtures, exemplars) → `docs/code-maps/wiremock-gateway-stubs.md` *(per-repo map, written by the pattern-scanner — resolves once harvested)*

## Guardrails (what NOT to do)
- Don't hit the real remote in a unit/slice test — stub it.
- Don't assert only the response; verify the request the client sent too.
- Don't leave stubs bleeding across tests — reset per test.

## Definition of done
- [ ] Client base URL bound to the WireMock port; happy + error + timeout stubs; request verified; isolated per test.
