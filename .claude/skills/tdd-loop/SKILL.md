---
name: tdd-loop
description: Red-green-refactor — one failing test first, minimal code, refactor under green. Use when implementing criteria.
---
# TDD loop
> **Generic "how" only.** Zero project nouns (no test-runner names, framework tags, module roots, fixture names). Link a docs leaf for any project fact. See `ARCHITECTURE.md` §1 (blueprint repo).

## When to use
Turning acceptance criteria into code one behavior at a time. When each requirement can be pinned by a test before it exists — and you want the tests to double as the behavior spec.

## How
- **Red first.** Pick *one* behavior from the criteria; write a test that fails for the right reason. Never write production code without a failing test demanding it.
- **Watch it fail.** Run it — confirm the failure is the expected one, not a typo or wiring error.
- **Green minimal.** Write the least code that makes it pass; fake or hardcode if that's smallest. Don't build ahead of the test.
- **Refactor under green.** Clean names, dedupe, extract — with the bar green the whole time. Revert if it goes red.
- **Small steps.** One behavior per cycle; commit each green. Name tests as the behavior they assert — the suite reads as the spec.

## Pattern signals (discovery cues — how the scanner recognizes this in any codebase)
- Test files paired 1:1 with units; behavior-phrased test names ("returns…/rejects…when…").
- Commit history alternating test + implementation in small increments; a fast unit-test task in CI.

## Project specifics → see docs
- Code map (test-runner setup, naming conventions, exemplar cycles) → `docs/code-maps/tdd-loop.md` *(per-repo map, written by the pattern-scanner — resolves once harvested)*

## Guardrails (what NOT to do)
- Don't write production code with no failing test asking for it — that's the whole discipline.
- Don't skip watching the test fail; a test that never went red proves nothing.
- Don't refactor while red, and don't add untested behavior "while you're there".
- Don't cram many behaviors into one cycle — split them.

## Definition of done
- [ ] Each behavior introduced via a test that failed first, then passed on minimal code.
- [ ] Refactoring done only under green; suite green at the end.
- [ ] Test names read as the behavior spec; steps small and committed per cycle.
