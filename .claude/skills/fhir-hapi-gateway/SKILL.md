---
name: fhir-hapi-gateway
description: HAPI FHIR R4 client for authenticated search and transactions. Use for outbound FHIR integrations.
---
# FHIR gateway with HAPI (R4)

> **Generic "how" only.** No endpoint URLs, resource profiles, or token specifics in the body — those
> live in the code-map leaf.

## When to use
Integrating a FHIR REST API (R4): searching resources, reading bundles, posting transactions, with
token-based auth and paginated results.

## How
- Create one configured `IGenericClient` (R4 `FhirContext`) per FHIR endpoint; reuse it (context
  creation is expensive).
- Attach auth via a client interceptor (e.g. `BearerTokenAuthInterceptor`); source the token from the
  auth boundary, never inline it.
- Use the fluent search/transaction API; follow `Bundle.link[next]` to page through large result sets
  rather than assuming one page.
- Map FHIR resources to domain types at the boundary; catch `BaseServerResponseException` subtypes and
  translate to typed gateway exceptions.
- Wrap calls with a circuit breaker + fallback ([[resilience4j]]); cache idempotent reads where it helps.

## Pattern signals (discovery cues)
`ca.uhn.hapi.fhir:hapi-fhir-client` + `hapi-fhir-structures-r4` deps; `FhirContext.forR4()`;
`IGenericClient`; `BearerTokenAuthInterceptor`; `.search()/.transaction()` fluent calls; `Bundle` paging;
classes named `*FhirGateway`.

## Project specifics → see docs
- Code map (endpoints, auth/pseudonymization, resource mappings, exemplars) → `docs/code-maps/fhir-hapi-gateway.md` *(per-repo map, written by the pattern-scanner — resolves once harvested)*

## Guardrails (what NOT to do)
- Don't recreate `FhirContext` per call — it's heavyweight; build once.
- Don't stop at the first page — honor the `next` link.
- Don't leak raw FHIR errors or identifiers into logs/responses.

## Definition of done
- [ ] One reusable client per endpoint; auth interceptor wired; paginated search handled; resources mapped
  to domain; errors typed; an integration test stubs the FHIR server and verifies search + paging.
