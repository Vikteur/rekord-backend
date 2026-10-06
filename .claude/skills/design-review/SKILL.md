---
name: design-review
description: Critique a design before build — assumptions, trade-offs, failure modes. Use for pre-build or refactor review.
---
# Design Review

> **Generic "how" only.** Zero project nouns. The architecture constraints and prior decisions to
> weigh against live in docs leaves, referenced below. See `ARCHITECTURE.md` §1 (blueprint repo).

## When to use
Before building something non-trivial, or to frame a refactor: when the question is *how should this
be shaped* and the cost of getting it wrong is high. Judgment, not mechanical checks. This runs
*before* the build; reviewing a part once it is green is [[code-review-process]].

## How
- **Name the assumptions** the design rests on; mark which are load-bearing and which are guesses.
- **Weigh ≥2 alternatives**, not just the proposed one; state the trade-offs (coupling, cost,
  reversibility, blast radius) and why the choice wins.
- **Check fit to the architecture** ([[clean-architecture]]) — does it respect layer boundaries,
  dependency direction, and existing seams? Flag where it fights the grain.
- **Probe failure modes**: what happens under error, load, partial failure, concurrency, rollback?
- **Prefer reversible, small-step designs**; call out one-way doors explicitly.
- Output a **verdict + the trade-offs + open risks**, not a redesign — the team decides.

## Pattern signals (discovery cues — how the scanner recognizes this in any codebase)
- ADRs / design-docs / RFCs in the repo; "decision/rationale" tables in docs.
- Architecture-fitness tests (the encoded constraints a design must satisfy).

## Project specifics → see docs
- Code map (ADR location, architecture constraints, prior decisions) → `docs/code-maps/design-review.md` *(per-repo map, written by the pattern-scanner — resolves once harvested)*

## Guardrails (what NOT to do)
- Don't review without considering an alternative — a one-option "review" is a rubber stamp.
- Don't redo mechanical checks a hook owns; focus on judgment and trade-offs.
- Don't smuggle a behavior change into a design framed as a refactor.

## Definition of done
- [ ] Assumptions named; ≥2 alternatives weighed with trade-offs.
- [ ] Architecture fit and failure modes assessed; one-way doors flagged.
- [ ] Verdict + open risks recorded for the team to decide.
- [ ] Verified by: a written design record another reviewer can disagree with — alternatives, trade-offs and one-way doors on the page, not in the conversation.
