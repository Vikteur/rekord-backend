---
name: gateway-client-hygiene
description: Port inside, client in the adapter, wire-to-domain mapping and typed errors at the edge. Use when building a gateway.
---
# Gateway client hygiene

> **Generic "how" only.** No concrete service/client names in the body — those live in the code-map.

## When to use
Building or reviewing an outbound integration (HTTP/SOAP/FHIR client) so transport concerns stay at the
boundary and never leak into domain/use-case code.

## How
- Declare the dependency as a **port interface in the inner layer** (use-case/domain owns the contract);
  the gateway in the adapter layer **implements** it. Inner code depends on the port, not the client.
- Translate wire types ↔ domain types **at the edge**; never let generated/transport DTOs flow inward.
- Map transport failures (timeouts, 4xx/5xx, faults) to **typed gateway exceptions**; don't leak raw
  client exceptions ([[exception-to-http]] maps them later).
- Apply resilience + caching at the boundary ([[resilience4j]], [[spring-caching]]); keep auth/token
  handling in config/interceptors, not in business calls.
- Keep the client stateless and configured once (base URL, auth, timeouts externalized).

## Pattern signals (discovery cues)
A use-case-layer interface implemented by an adapter-layer `*Gateway`/`*Client`; mapping between
generated/transport models and domain at the boundary; typed gateway exceptions; resilience annotations.

## Project specifics → see docs
- Code map (port↔gateway pairs, mapping + error conventions, exemplars) → `docs/code-maps/gateway-client-hygiene.md` *(per-repo map, written by the pattern-scanner — resolves once harvested)*

## Guardrails (what NOT to do)
- Don't let transport DTOs or client exceptions cross into domain/use-case code.
- Don't put the integration contract in the adapter — the inner layer owns the port.
- Don't scatter auth/timeout config through call sites — centralize it.

## Definition of done
- [ ] Port in the inner layer, client in the adapter; wire↔domain mapped at the edge; typed errors; resilience + auth centralized; an integration test covers a failure path.
