---
name: auth-context-facade
description: Resolve the authenticated principal into a domain value object at the boundary. Use for authenticated flows.
---
# Authenticated-principal context

> **Generic "how" only.** No concrete principal type/claim names in the body — those live in the code-map.

## When to use
Any flow that needs the current user's identity/claims in the inner layers (use-case/domain) without
those layers depending on the web/security framework.

## How
- Resolve the principal **once, at the adapter boundary** (from the security context / token) into a
  small **domain value object** carrying just the identity + claims the inner layers need.
- Pass that value object **inward as a method parameter**; inner code depends on it, not on the
  framework's `Authentication`/`Principal`/token types.
- Keep the value object immutable; expose intent-named accessors (active identity, roles) — not the raw token.
- Resolve sensitive identifiers through the boundary helpers ([[identifier-pseudonymization]]); don't
  rebuild the principal deep in the call stack.

## Pattern signals (discovery cues)
A domain value object representing the authenticated user threaded as a parameter through use-cases;
resolution from the security context confined to the adapter layer; inner layers free of framework auth types.

## Project specifics → see docs
- Code map (the principal type, where it's resolved, exemplars) → `docs/code-maps/auth-context-facade.md` *(per-repo map, written by the pattern-scanner — resolves once harvested)*

## Guardrails (what NOT to do)
- Don't leak framework security types (`Authentication`, token) past the adapter.
- Don't re-resolve the principal in multiple places — resolve once, pass it.
- Don't expose the raw token on the value object — only the identity/claims needed.

## Definition of done
- [ ] Principal resolved once at the boundary into an immutable domain value object; passed inward as a param; inner layers free of framework auth types.
- [ ] Verified by: a use-case-layer test constructing the principal value object directly, with no framework auth type on the test classpath.
