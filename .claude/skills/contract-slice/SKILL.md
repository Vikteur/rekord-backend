---
name: contract-slice
description: Slice an API contract to one tag or operation, self-contained and lintable. Use when an agent needs a slice.
---
# Contract slice

> **Generic "how" only.** Zero project nouns — the spec source, slicer script, tag names, and
> component roots live in the code-map docs leaf, referenced below. See `ARCHITECTURE.md` §1 (blueprint repo).

## When to use
A downstream agent needs the part of an API contract relevant to one capability, and the full spec is
too large to hand it. Use when scoping context by tag or operation — read the whole spec once, then
emit a self-contained excerpt so consumers get only the slice, never the entire document.

## How
- **Single full-reader, many slices** — one pass over the whole spec produces the excerpt; downstream
  agents read the slice, not the source. A token-budget rule, not a nicety.
- **Select by tag or operationId** — pick the operations the task needs; the tag/operation is the seam,
  everything else is noise to drop.
- **Pull `$ref`s transitively** — walk from each selected operation into its request/response bodies,
  parameters, and responses, following every `$ref` to a fixed point so no referenced schema, enum, or
  shared response is left dangling.
- **Keep it self-contained** — the excerpt must resolve on its own: carry the shared components it
  references, keep `$ref` targets present, and preserve enough envelope (info, security, servers) that
  it parses and lints in isolation.
- **Slice deterministically** — prefer a script that parses, selects, and closes the ref graph over a
  model re-reading and retyping the spec; determinism beats a plausible-looking paraphrase.
- **Lint the output** — run the same ruleset the full spec passes; a slice that references a dropped
  component or breaks the schema is worse than no slice.

## Pattern signals (discovery cues — how the scanner recognizes this in any codebase)
- A large OpenAPI/Swagger document plus a slicer/extract script that takes a tag or operationId and
  emits a smaller spec; a ref-resolution/bundle step in the toolchain.
- Downstream agents/tasks fed a scoped excerpt rather than the full contract; a `$ref` graph closed
  over `components`; the slice re-run through the project lint ruleset.

## Project specifics → see docs
- Code map (spec source, slicer script, tag/operation taxonomy, component roots, lint ruleset,
  exemplars) → `docs/code-maps/contract-slice.md` *(per-repo map, written by the pattern-scanner — resolves once harvested)*

## Guardrails (what NOT to do)
- Don't hand the whole spec to a downstream agent when a tag/operation slice suffices — that's the
  budget leak this skill exists to stop.
- Don't emit a slice with unresolved `$ref`s — close the ref graph transitively before writing.
- Don't have a model retype or paraphrase the spec — slice it deterministically from the source.
- Don't skip linting the excerpt against the project ruleset.

## Definition of done
- [ ] Slice scoped to the selected tag/operation; unrelated operations dropped.
- [ ] All `$ref`s resolved transitively; excerpt is self-contained and parses in isolation.
- [ ] Produced deterministically (script, not paraphrase) and lints clean against the ruleset.
