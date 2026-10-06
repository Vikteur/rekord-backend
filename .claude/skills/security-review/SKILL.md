---
name: security-review
description: Review a diff for secrets, PII exposure, authn/authz, transport, and audit gaps. Use on sensitive changes.
---
# Security review
> **Generic "how" only.** Zero project nouns (no identifier names, gateway names, config keys, package roots). Link a docs leaf for any project fact. See `ARCHITECTURE.md` §1 (blueprint repo).

## When to use
A diff touches a security-sensitive surface — authentication/authorization config, a change to how a personal identifier or other PII is stored/logged/returned, an external integration that signs or encrypts messages, audit logging, secret/config handling, error responses, or a bump of a security-relevant dependency. Runs **in addition to** the normal code review ([[code-review-process]]), not instead of it. If nothing sensitive changed, skip.

## How
Walk the diff and apply only the dimensions whose changed files match. Classify each finding and state *why it matters* with a concrete authority (a regulation, a project rule, a threat) — abstract advice ("validate input") is unhelpful.

- **Severity:** **Critical** (confidentiality/integrity/auth regression — must fix before merge) · **Warning** (defense-in-depth gap — should mitigate) · **Suggestion** (hardening, optional).
- **Secrets & config** — no secret/key/password committed (even as a placeholder that survived a revert); secrets come from env/secret store; TLS verification never disabled (no trust-all / allow-all hostname), including in tests.
- **Identifier / PII handling** — sensitive identifiers stored only encrypted; never in logs, exception messages, response bodies, cache keys, or URIs (data minimisation); masked at every sink.
- **Authn / authz** — every new/relaxed public route and CSRF/CORS change called out with the exact path and exposed surface; object-level checks (principal-vs-target) on any operation over another subject's data; credentials/token lifetimes not weakened; filter-chain order preserved.
- **Transport & message security** — message signing/encryption stays enabled on external calls; issued tokens/assertions validated for audience + lifetime; short-lived tokens not cached past their expiry; decrypted sensitive payloads never logged or committed as fixtures.
- **Audit & observability** — an audit entry removed for a previously-audited action needs explicit justification; audited PII redacted at the sink.
- **Error responses** — no stack traces / internal paths to the client; responses don't vary in a way that reveals whether a record exists (enumeration); validation errors don't echo the sensitive value back.
- **Dependency-triggered** — on a security-relevant dependency bump, read release notes for behavioural changes (e.g. default filter-chain order), reject `@SuppressWarnings("deprecation")` that silences a security deprecation, and confirm a CVE scan ran.

## Finding format
State severity, location (`file:line`), what the code does, why it's wrong, and the fix. **"Why" means a named authority from the project's code map — a regulation article, a platform convention, or a written project rule — not a restatement of the finding.** "Don't log identifiers" is advice a reader can dismiss; "GDPR Art. 5(1)(c) data minimisation" is one they have to argue with, and it tells them which other cases it also covers.

If the code map names no authority for the surface you are reviewing, say so in the finding and flag the gap — do **not** invent a citation. A wrong article is worse than none, because it will be quoted back in the next review and nobody re-checks it.

Example: `**[CRITICAL]** national identifier logged in plaintext at path:line — <the authority the code map names for identifiers in logs> forbids this even at DEBUG; mask or drop it.`

## Pattern signals (discovery cues)
- Changes under auth/security config, encryption utilities, gateways/clients to external services, audit, or the global error handler.
- New env vars / config keys; dependency-lockfile changes on security libraries.

## Project specifics → see docs
- Code map (**the governing authorities — which regulation or platform convention binds each surface**, plus the sensitive files/globs, encryption entry points, filter-chain layout, external-integration security rules, audit sink, error-handler contract, secret config locations) → `docs/code-maps/security-review.md`
- **Read it before reviewing, every time.** Regulatory and organisational obligations are the one class of requirement that is absent from a model's training data and cannot be inferred from the code: nothing in a repository tells you which identifier is a national identifier, which payload is a special category, or how long anything may be retained. Every other section of this skill is a method you can apply from first principles. This one you cannot.

## Guardrails (what NOT to do)
- Don't pass a security-sensitive diff with "looks fine" — name each dimension you checked or state it didn't apply.
- Don't restate generic conventions the code-style/shared instructions already own; carry only the **review angle**.
- Don't treat a placeholder secret as safe — a committed secret is compromised regardless of value.
- Don't defer a Critical to a follow-up ticket; confidentiality/integrity/auth regressions block the merge.
- Don't invent a regulation, article, or convention to make a finding sound authoritative — cite what the code map names, or say the authority is missing.
- Don't treat a clean secret-scan or PII-lint run as having done this review; those catch the literal cases, which are the ones least likely to survive to a PR.

## Definition of done
- [ ] Every dimension whose files changed was applied (or explicitly N/A).
- [ ] Each finding carries severity + location + why + fix, and every "why" cites an authority the code map names.
- [ ] No Critical left open; Warnings have an owner or a tracked follow-up.
- [ ] Verified by: the policy gate green on the PR, and every Critical either fixed in the diff or written up with a named owner.
