---
paths:
  - "**/application/**"
  - "**/logging/**"
  - "**/encryption/**"
---
# Platform layer — always-on guardrails

> **Backstop, not a knowledge store.** Always-on for the runnable application module and the shared
> cross-cutting libraries — keep tiny and **project-noun-free**. **Hard cap: ≤5 invariant lines**;
> depth → `bean-config-di` / `aes-gcm-encryption` / `exception-to-http` skills (lazy), facts →
> `docs/code-maps/security-review.md`. Do not restate skill steps here. See `ARCHITECTURE.md`
> §2 (caution), §3 (blueprint repo).

- This is where security config, filter chains, aspects and exception handling live: a change here
  applies to every capability at once, so treat the blast radius as repo-wide.
- Authentication, authorization and the access matrix are STOP-gated — propose, do not apply.
- What gets logged is a policy decision, not a convenience: personal identifiers are masked at the
  point of logging, and the audit trail is append-only.
- Wiring belongs here; business logic does not. Configuration classes assemble collaborators and
  nothing else.
- Time, randomness and encryption come from the shared abstractions — never from a direct static call.
