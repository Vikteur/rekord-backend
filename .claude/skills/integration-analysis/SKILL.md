---
name: integration-analysis
description: Identify external integrations — gateways, datastores, caches, queues. Use when onboarding.
---
# Integration analysis

> **Generic "how" only.** Zero project nouns. The concrete services, gateways, and resilience recipes
> you find are written to the inventory / integration code-maps, referenced below. See `ARCHITECTURE.md` §1 (blueprint repo).

## When to use
On onboarding — when you need the map of external systems and the resilience/security recipes around
them, to record integrations and seed gateway/resilience skills.

## How
- **Inventory the outbound integrations**: every external system the code talks to — datastores,
  caches, message queues, third-party HTTP/SOAP/gRPC services, identity providers, file/blob stores.
- **For each**, record the client/gateway class, the protocol, where its config/credentials come from,
  and the boundary layer it lives in (it should be an adapter, not the domain).
- **Capture the resilience posture**: timeouts, retries, circuit breakers, rate limits, caching, and
  fallbacks — and whether they're applied consistently.
- **Note cross-cutting concerns** at the boundary: auth/token exchange, encryption, audit logging, PII
  handling — anything a reviewer must check when code touches that seam.
- **Surface recurring integration patterns** as candidate skills for the skill-harvest pass.
- Cite the gateway/config file for every integration; mark unconfirmed endpoints `TODO(verify)`.

## Pattern signals (discovery cues — how the scanner recognizes this in any codebase)
- HTTP/RPC clients, ORM/repository config, driver dependencies (DB, cache, broker), SDKs for cloud/third-party services.
- Connection/endpoint config: env vars, `application*.yml`/`.properties`, `*.env`, secrets references,
  service-discovery config.
- Resilience/caching markers: circuit-breaker/retry/rate-limiter annotations or wrappers, cache
  annotations, timeout settings.

## Project specifics → see docs
- The discovered facts (with provenance) → `docs/_inventory/70-dependency-integration-analyst.md`
- The integration code-maps it seeds → `docs/code-maps/README.md`

## Guardrails (what NOT to do)
- Don't report an integration that's only a transitive dependency — confirm the code actually calls it.
- Never copy secrets or credential values into the inventory; record the *source* of config, not its value.
- Keep concrete service/endpoint names out of this skill body — they live in the inventory / code-map leaf.

## Definition of done
- [ ] Every outbound integration listed with its client/gateway, protocol, config source, and boundary layer.
- [ ] Resilience and security posture captured per integration.
- [ ] Recurring integration patterns surfaced as skill candidates; each fact sourced to a file.
