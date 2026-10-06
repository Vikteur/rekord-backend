---
name: resilience4j
description: Resilience4j circuit breakers, retries, and fallbacks on outbound calls. Use for any gateway or remote call.
---
# Resilience4j — circuit breakers, retries, fallbacks

> **Generic "how" only.** No service names, endpoints, or instance names in the body — those live in
> the code-map leaf.

## When to use
Adding fault tolerance to an outbound call (HTTP/SOAP/FHIR client) so a slow or failing dependency
degrades gracefully instead of cascading: circuit breaker, retry, rate limiter, time limiter, fallback.

## How
- Annotate the gateway method: `@CircuitBreaker(name = "<instance>", fallbackMethod = "<fallback>")`
  (optionally `@Retry`, `@RateLimiter`, `@TimeLimiter`). The fallback must share the method signature
  plus a trailing `Throwable` parameter.
- Configure each named instance in application config (failure-rate threshold, wait-duration-in-open,
  sliding-window type/size, slow-call thresholds). One instance per dependency, not one global.
- Make the fallback meaningful: a cached/empty/typed-degraded result, or a domain exception that maps
  to a clear HTTP status — never swallow the error silently.
- Expose `register-health-indicator: true` so the breaker state surfaces in the health endpoint; keep
  that endpoint authenticated.

## Pattern signals (discovery cues)
`io.github.resilience4j:resilience4j-spring-boot3` on the classpath; `@CircuitBreaker` / `@Retry` /
`@RateLimiter` / `@TimeLimiter` annotations on gateway/client classes; `fallbackMethod = ` references;
per-instance keys under a `resilience4j.*` config tree.

## Project specifics → see docs
- Code map (configured instances, thresholds, fallbacks, exemplars) → `docs/code-maps/resilience4j.md` *(per-repo map, written by the pattern-scanner — resolves once harvested)*

## Guardrails (what NOT to do)
- Don't share one breaker instance across unrelated dependencies — tune per integration.
- Don't let a fallback hide a bug: log it, and don't return success-shaped data for a hard failure.
- Don't put a circuit breaker on a fast in-process call — it's for remote/IO boundaries.

## Definition of done
- [ ] Each outbound dependency has its own named breaker + a typed fallback; thresholds configured; health
  indicator on; a test proves the fallback path fires when the breaker is open.
