---
name: validation-notification-result
description: Accumulate validation errors in a Notification result instead of throwing on the first. Use when validating input.
---
# Validation Notification (collected-errors result)

> **Generic "how" only.** Zero project nouns. The result type's location, its factory conventions
> and exemplars go in the code-map docs leaf, referenced below. See `ARCHITECTURE.md` §1 (blueprint repo).
>
> Not to be confused with *delivery* notifications — sending messages to users over channels, a
> separate concern (the `notification-pattern` skill, in bundles that carry it); this one is the GoF
> *Notification* validation pattern: a Result-style object that collects rule violations.

## When to use
Validating anything that can fail in several independent ways at once — domain factories and
create-requests, use-case argument validation, per-item checks in batch/scheduled jobs — where the
caller needs the complete list of problems, not just the first one hit.

## How
- Validators **return a result object**, they do not throw: a small collector with
  `addError`/`addWarning`, `hasErrors()`/`hasWarnings()`, and joined message accessors. Exceptions
  stay reserved for *unexpected* failures, not expected validation outcomes.
- **Evaluate every rule**, accumulating as you go — never short-circuit on the first violation;
  the value of the pattern is the complete picture in one pass.
- **Decide once, at the boundary**: after validation completes, exactly one caller checks
  `hasErrors()` and converts the outcome (reject the request, skip the batch item and record it,
  abort construction). Interior code passes the result along instead of branching repeatedly.
- Provide **composition helpers**: an empty instance, a single-error factory, a merge of several
  results, and a fluent add of a nested result — composite validations combine child results
  instead of re-validating.
- Keep **warnings separate from errors**: warnings inform the caller and never block the operation.
- In **factories**, validate-then-construct: run validation first, construct the object only when
  the result is clean, so invalid instances are unrepresentable.
- In **batch/scheduled work**, collect a per-item result and aggregate into a job-level outcome —
  one bad item must not abort the run.

## Pattern signals (discovery cues — how the scanner recognizes this in any codebase)
- A small class named like `Notification`/`ValidationResult`/`Errors` holding message lists with
  `hasErrors()`/`isValid()` and joined-message accessors.
- Factory or validator methods returning that type rather than throwing; call sites branching on
  `hasErrors()` after validation.
- Static composition helpers (`empty()`, `of(...)`, `merge(...)`) and results being combined
  across nested validations.
- Scheduled/batch code accumulating per-item results into a run summary.

## Project specifics → see docs
You can find worked examples of this pattern, and the conventions this project actually follows, in
the code map → `docs/code-maps/validation-notification-result.md` *(lazy — read on demand)*. Each
exemplar there points straight to the file that demonstrates it.

## Guardrails (what NOT to do)
- Don't throw inside validators for expected rule violations — collect them; control-flow
  exceptions hide all but the first problem.
- Don't decide in the middle: interior code adds to the result, only the boundary interprets it.
- Don't grow the result object into domain logic — it stays a dumb message collector.
- Don't drop warnings silently: surface them to the caller even when the operation proceeds.
- Don't confuse this with sending user-facing notifications — delivery over channels is a separate
  concern (the `notification-pattern` skill, in bundles that carry it).

## Definition of done
- [ ] Every validator returns the result object; no expected-failure exceptions remain.
- [ ] All rules evaluate in one pass; messages aggregate deterministically.
- [ ] Exactly one boundary maps `hasErrors()` to the transport-appropriate failure.
- [ ] Tests assert the full error list (and warnings), not just the first violation.
