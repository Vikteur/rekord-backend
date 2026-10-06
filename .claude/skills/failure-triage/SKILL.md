---
name: failure-triage
description: Diagnose failures evidence-first — reproduce, isolate, prove root cause before fixing. Use when a run is red.
---
# Failure Triage

> **Generic "how" only.** Zero project nouns. Where logs/artifacts live and project repro commands
> go in the code-map docs leaf, referenced below. See `ARCHITECTURE.md` §1 (blueprint repo).

## When to use
A red CI run, a failing test, a production error, or a bug report — whenever you don't yet know
*what's wrong*. Diagnosis-first: **no edits until the cause is proven.**

## How
- **Reproduce first.** Establish a *deterministic* repro — a failing test, a request, a log
  signature. If you can't reproduce, that **is** the finding: escalate "cannot reproduce, need X."
- **Isolate by bisecting scope, not guessing.** Narrow to a layer / module / commit range. Read only
  the relevant docs leaf + the suspect Declared Files — never the whole repo.
- **Prove the cause with evidence.** Not "I think it's the cache" but "X is missing on Y, confirmed
  by test Z going green when added." A cause without a confirming signal is a hypothesis, not a cause.
- **Write the finding** as `{root cause, affected part, suggested fix, evidence}` — hand off; don't
  fix here. The fix goes through the test-first sub-loop (regression test red → implement → green).
- **Time-box** under incident pressure: just enough repro to prove the cause, then stabilize.

## Pattern signals (discovery cues — how the scanner recognizes this in any codebase)
- CI logs / failed-run artifacts; stack traces; flaky-test retry config.
- A debug/postmortem artifact convention (`debug.md` / `incident.md`).
- Repro tests named for a bug/ticket id; regression tests added alongside fixes.

## Project specifics → see docs
- Code map (where logs/artifacts live, repro commands, known flaky areas) → `docs/code-maps/failure-triage.md` *(per-repo map, written by the pattern-scanner — resolves once harvested)*

## Guardrails (what NOT to do)
- Don't edit code while triaging — diagnosis and fix are separate roles (structural separation).
- Don't claim a root cause without a confirming signal (evidence rule).
- Don't fix a symptom; trace to the cause or escalate.

## Definition of done
- [ ] Deterministic repro established (or "cannot reproduce" escalated).
- [ ] Root cause proven with cited evidence; finding written for handoff.
- [ ] A regression test is specified so the bug can't silently return.
