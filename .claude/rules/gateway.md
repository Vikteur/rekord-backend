---
paths:
  - "**/*-gateway/**"
  - "**/gateway/**"
  - "**/*-gateway-api/**"
---
# Gateway layer — always-on guardrails

> **Backstop, not a knowledge store.** Always-on for any edit in an outbound-integration module —
> keep tiny and **project-noun-free**. **Hard cap: ≤5 invariant lines**; depth →
> `gateway-client-hygiene` / `soap-cxf-gateway` / `fhir-hapi-gateway` / `resilience4j` skills (lazy),
> facts → `docs/code-maps/gateway-client-hygiene.md`. Do not restate skill steps here. See `ARCHITECTURE.md`
> §2 (caution), §3 (blueprint repo).

- Gateways isolate the outside world: no third-party SDK, wire or generated-binding type crosses
  outward past this layer.
- Every remote call carries the resilience policy (timeout, retry, circuit breaker) and a fallback
  that degrades rather than propagates a transport failure.
- Credentials, tokens and identifiers are obtained and exchanged here — never constructed inline, and
  never logged. Personal identifiers are pseudonymized before they leave.
- Translate remote faults into this system's exception vocabulary at the boundary; callers see
  domain-shaped failures, not HTTP or SOAP ones.
- No business decisions here — a gateway fetches and maps, the usecase decides.
