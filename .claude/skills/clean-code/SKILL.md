---
name: clean-code
description: Small focused units, intention names, no duplication, guard clauses. Use whenever writing or refactoring code.
---
# Clean Code

> **Generic "how" only.** Zero project nouns. Project facts (style config, naming conventions, where
> exemplars live) go in the code-map docs leaf, referenced below. See `ARCHITECTURE.md` §1 (blueprint repo).

## When to use
Any time you add or change code, and during review. The baseline every other skill assumes: it governs
how a unit is written. *Where* that unit belongs is a placement question — [[clean-architecture]]; the
idiom it is written in is the side's language skill (`java` / `typescript`, whichever the bundle carries).

## How
- One unit, one responsibility; keep functions short and at a single level of abstraction.
- Names reveal intent; avoid abbreviations and encodings. A comment that restates the code is a
  smell — make the code say it.
- Guard clauses over nested conditionals; return early. Keep nesting shallow.
- No duplication: extract the third occurrence. Prefer composition over inheritance.
- Make illegal states unrepresentable (types/value objects) rather than validating everywhere.
- Leave the campsite cleaner: small, safe refactors alongside the change you came to make.

## Pattern signals (discovery cues — how the scanner recognizes this in any codebase)
- Linter/formatter config present (e.g. `.editorconfig`, checkstyle/eslint configs).
- Recurring helper/util modules; consistent guard-clause and early-return style.
- Value-object / wrapper types used instead of primitives for domain values.
- Test or review tooling that flags complexity/duplication (cyclomatic, copy-paste detectors).

## Project specifics → see docs
- Code map (style config, naming, exemplars, anti-patterns to avoid) → `docs/code-maps/clean-code.md` *(per-repo map, written by the pattern-scanner — resolves once harvested)*

## Guardrails (what NOT to do)
- Don't add comments to explain unclear code — rename/restructure instead.
- Don't grow a function past one screen or one level of abstraction (hook: complexity gate).
- Don't copy-paste a block a third time (hook: duplication gate).

## Definition of done
- [ ] Units small and single-purpose; names self-explanatory.
- [ ] No new duplication; no dead code.
- [ ] Formatter/linter clean.
