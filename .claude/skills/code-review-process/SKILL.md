---
name: code-review-process
description: Review a part scoped to its files, then one integration pass over the seams. Use when a part goes green.
---
# Code review process

> **Generic "how" only.** Zero project nouns. What the part declares, which layer skills apply, and
> where the overview lives are pipeline facts in the code-map docs leaf, referenced below. See
> `ARCHITECTURE.md` §1 (blueprint repo).

## When to use
When a part turns **green** (its checks/hooks pass) and it needs a review before hand-off. This is the
*process* — how to run the pass; the judgment lens itself is a separate skill: the part's layer skills
carry the domain lens, [[security-review]] runs alongside on a sensitive diff. Not for pre-build
framing — that is [[design-review]].

## How
- **Scope tight**: review only the part's **declared files** plus the **acceptance-criteria slice** it
  claims — not the whole tree, not files it never touched.
- **Review through the part's layer skills** as the lens — apply each declared layer's checklist to its
  own files; don't invent criteria the part didn't sign up for.
- **Don't re-run mechanical checks** a hook already owns (build, tests, arch-fitness) — the part is
  green; review what judgment must catch.
- **One thin integration pass**, last: read the combined overview and check the **seams** — contracts,
  data direction, and shared assumptions between this part and its neighbors. Thin, not a re-review.
- **Output a verdict + a ranked must-fix list** (most-blocking first) — findings, not a rewrite; the
  author fixes. Note nice-to-haves separately so they don't block.
- **Keep it a summary hand-off**: cite file + reason per finding; no inline patch dumps.

## Pattern signals (discovery cues — how the scanner recognizes this in any codebase)
- A per-part / per-slice pipeline where each part declares its own files and acceptance criteria.
- Per-layer review checklists or path-scoped rules (`.claude/rules/*.md`) scoped to a layer.
- A green-gate (passing hooks/CI) that precedes a human/agent review step; a combined-overview artifact.

## Project specifics → see docs
- Code map (part manifest shape, layer-skill mapping, overview location, verdict format) → `docs/code-maps/code-review-process.md` *(per-repo map, written by the pattern-scanner — resolves once harvested)*

## Guardrails (what NOT to do)
- Don't widen scope past the part's declared files + acceptance slice — a whole-tree sweep is a
  different job.
- Don't re-litigate green mechanical checks a hook owns; review judgment, not what CI already proved.
- Don't rewrite the code or emit patches — produce a ranked must-fix list and hand back.
- Don't let the integration pass balloon into a full second review; it's the seams only.

## Definition of done
- [ ] Review scoped to declared files + acceptance slice; each file reviewed via its layer skill.
- [ ] One thin integration pass over the combined overview covering the seams.
- [ ] Verdict + ranked must-fix list (each finding cited to a file); nice-to-haves kept separate.
- [ ] Verified by: a verdict artifact in the ticket docs folder whose every must-fix cites a file and line the author can open.
