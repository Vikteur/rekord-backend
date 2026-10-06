---
name: identifier-pseudonymization
description: Mask or pseudonymize personal identifiers before logging or sending them out. Use at integration boundaries.
---
# Identifier pseudonymization

> **Generic "how" only.** No real identifier formats, services, or test values in the body — those live
> in the code-map.

## When to use
Handling a sensitive personal identifier (national ID number, customer or account id) that must not appear in
plaintext in logs, cache keys, or outbound payloads to a third party.

## How
- Pseudonymize via the dedicated service/token before the value crosses a boundary; pass the
  pseudonymized token outward, never the raw identifier.
- Mask in logs and error messages (redact to a fixed shape); never log the full value.
- If the value must be a cache key, key on the pseudonymized/hashed form, not the raw identifier.
- Provide an **environment-specific test override** (a safe non-production value) so lower environments
  never transmit a real identifier.
- Keep the mapping raw↔pseudonym out of application code — it belongs to the auth/boundary layer.

## Pattern signals (discovery cues)
A pseudonymization client/token at gateway boundaries; redaction helpers around logging; cache keys
built from a token rather than the raw id; an env-gated test-identifier substitution in a gateway.

## Project specifics → see docs
- Code map (the pseudonymization flow, redaction, test overrides, exemplars) → `docs/code-maps/identifier-pseudonymization.md` *(per-repo map, written by the pattern-scanner — resolves once harvested)*

## Guardrails (what NOT to do)
- Don't log or cache-key the raw identifier — pseudonymize/redact first.
- Don't ship a real identifier to a non-production external system.
- Don't scatter the raw↔pseudonym mapping through business code.

## Definition of done
- [ ] Raw identifier never logged/transmitted in plaintext; cache keys use the token; env test-override in place; a test proves redaction.
