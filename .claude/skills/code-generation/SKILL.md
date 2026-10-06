---
name: code-generation
description: Generate code from a contract or schema source of truth, regenerated on change. Use when generating code.
---
# Code generation

> **Generic "how" only.** Zero project nouns (no generator names, template paths, output dirs, package
> roots). Link a docs leaf for any project fact. See `ARCHITECTURE.md` §1 (blueprint repo).
>
> Absorbs the former `openapi-contract-workflow` skill — conforming a server to an upstream-owned
> spec is this skill applied to a contract.

## When to use
When a shape is derivable from a **source of truth** — a contract, schema, entity, or template — and
hand-writing it would duplicate that truth. Reach for scaffolding/codegen instead of typing the artifact
by hand, and whenever the same boilerplate recurs across many files. This includes implementing or
maintaining a server against an upstream-owned OpenAPI contract (api-first): the spec is the source of
truth and your job is to conform to it.

## How
- **Generate from one source of truth.** Point the generator at the contract/schema/template; never let
  two hand-maintained copies of the same shape drift apart. Types the contract defines are generated artifacts.
- **Never hand-edit generated output — regenerate.** Change the source or the generator config, then
  re-emit. Patches to generated files are lost on the next run.
- **Regenerate on every source change as the first step of the task**; treat generation as build input,
  then adapt the implementation to the new generated interface.
- **Adapt code to the generated seam, never the reverse** — if the shape is wrong, fix it upstream in
  the source and regenerate, don't patch the output. Keep contract-shaped types on one side, business
  logic on the other, mapped across explicitly — don't let generated types leak past the seam.
- **Keep generated artifacts out of VCS, or clearly separated.** Gitignore the output dir, or mark it
  (path/header banner) so no one mistakes it for hand-written code.
- **Make generation deterministic and reproducible.** Pin generator version and inputs; same source in ⇒
  same bytes out. Wire it into the build graph and re-run in CI to catch drift.
- **Review generated output like any code.** Diff what codegen produces; a bad template ships bugs at scale.
- **Customize via the generator, not the artifact** — templates, config, hooks — so customization survives regen.

## Pattern signals (discovery cues — how the scanner recognizes this in any codebase)
- A generator plugin/CLI in the build wired to a source-of-truth input (spec/schema/IDL/template).
- A generated-output dir that is gitignored or carries a "do not edit / generated" banner.
- A build task that emits code and a compile step depending on it; a CI step that regenerates and diffs.
- Generated interfaces/DTOs the server implements or maps to; an explicit mapper layer between
  generated types and domain types.

## Project specifics → see docs
- Code map (generators, sources of truth, output locations, seam/mapper conventions, exemplars) → `docs/code-maps/code-generation.md` *(per-repo map, written by the pattern-scanner — resolves once harvested)*

## Guardrails (what NOT to do)
- Don't hand-edit generated files — change the source or template and regenerate.
- Don't hand-write a type the source of truth owns — a hand-authored contract DTO is a drift bug waiting to happen.
- Don't shape an upstream-owned source to fit the implementation — the contract is owned upstream; adapt to it.
- Don't leak generated types past the seam into business logic — map at the boundary.
- Don't commit generated artifacts mixed in with hand-written code; gitignore or clearly separate them.
- Don't let generation be non-deterministic (unpinned versions, ambient inputs) — CI can't detect drift.
- Don't skip review of generated output because "the tool made it" — a template bug scales.

## Definition of done
- [ ] Artifact generated from a single source of truth via a pinned, deterministic generator; regenerated
      from the current source as the first step of the task.
- [ ] Output gitignored or clearly separated and unedited; regenerating from a clean checkout is a no-op.
- [ ] Generated types mapped to domain at the seam, not leaked past it; no hand-written types the source owns.
- [ ] Generation runs in the build graph and CI diffs it; generated output was reviewed.
