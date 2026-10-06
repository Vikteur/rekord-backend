---
name: exception-to-http
description: Map a domain exception hierarchy to HTTP status via one controller-advice. Use when surfacing REST errors.
---
# Exception-to-HTTP mapping

> **Generic "how" only.** No concrete exception/status mappings in the body — those live in the code-map.

## When to use
Turning typed domain/gateway exceptions into consistent HTTP responses (status + error body) without
try/catch scattered through controllers.

## How
- Define a small exception hierarchy (not-found, validation/conflict, upstream-unavailable, forbidden);
  throw the typed exception from the inner layers — controllers don't catch.
- Centralize translation in one `@RestControllerAdvice`; each handler maps an exception (family) to a
  status + a uniform error body. Map the **base** types, with overrides for specifics.
- Keep the error body shape consistent (code, message, optional details); never leak stack traces or
  internal identifiers.
- Default unmapped exceptions to 500 with a generic body, and log the detail server-side only.

## Pattern signals (discovery cues)
A `@RestControllerAdvice`/`@ControllerAdvice` with `@ExceptionHandler` methods; a domain exception base
class hierarchy; `ResponseEntity`/`ProblemDetail` error bodies; `@ResponseStatus` on exceptions.

## Project specifics → see docs
- Code map (the exception hierarchy → status table, handler exemplar) → `docs/code-maps/exception-to-http.md` *(per-repo map, written by the pattern-scanner — resolves once harvested)*

## Guardrails (what NOT to do)
- Don't catch exceptions in controllers — let the advice handle them.
- Don't leak stack traces, internal ids, or upstream messages to clients.
- Don't return 200 with an error payload — use the right status.

## Definition of done
- [ ] Typed exceptions thrown inward; one central advice maps families → status + uniform body; unmapped → 500 logged server-side; a test asserts the mapping.
