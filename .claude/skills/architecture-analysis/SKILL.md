---
name: architecture-analysis
description: Detect the layers, seams, and dependency direction of a codebase. Use when onboarding or slicing a feature.
---
# Architecture analysis

> **Generic "how" only.** Zero project nouns. The concrete layer names, package roots, and per-layer
> plan split you find are written to the layer model / inventory, referenced below. See `ARCHITECTURE.md` §1 (blueprint repo).
>
> Absorbs the former `architecture-blueprint` skill — one skill for both the onboarding pass and the
> pre-slicing blueprint.

## When to use
Two moments, same method: (1) on onboarding, after the repo structure is mapped — when you need to
name *the architectural style and its layers* so the framework can scope skills and plans per layer;
(2) before slicing a feature into per-layer work — when you need one blueprint that says *which
modules own what and where the change lands* so the pieces split cleanly. Judgment and mapping, not
code — read the tree and the import graph, don't edit them.

## How
- **Map modules → responsibilities**: one line per module — what it owns, what it must not.
- **Name the style** from evidence: clean/hexagonal (domain · use-case · adapter), MVC, feature-sliced,
  modular monolith, etc. Don't assume — infer from the directory shape and import graph.
- **Identify the layers/concerns** and the package root that marks each; record the naming shape that
  signals membership (suffix, folder, annotation).
- **Determine dependency direction**: sample imports across boundaries and state which way they point;
  flag violations (a "domain" that imports a framework, a UI that reaches a datastore directly).
- **Decide the per-layer plan split** the pipeline should use (one plan file per layer, or one for the
  side) from how independently the layers change.
- **Locate the contract/seam** between sides (if any) and how each side syncs to it.
- **Trace where a change lands** (pre-slicing use): for the feature at hand, list which layers it
  touches and in what order, so each layer becomes an independently slice-able unit with no
  cross-layer bleed.
- Record each call with a source path; mark unprovable structure `TODO(verify)`.

## Pattern signals (discovery cues — how the scanner recognizes this in any codebase)
- Directory/package names like `domain`, `usecase`/`application`, `adapter`/`infrastructure`,
  `ports`, `api`, `web`, `core`, `feature-*`, `lib/*`; one build root per module.
- Architecture-fitness tests or lint rules encoding dependency direction; layered build-module graphs.
- Import statements crossing layer folders (the real dependency direction).
- A contract artifact at the seam (OpenAPI/proto/GraphQL SDL) with client-gen config on the consumer side.

## Project specifics → see docs
- The discovered facts (with provenance) → `docs/_inventory/20-architecture-analyst.md`
- The completed model it fills → `docs/layer-model.md`

## Guardrails (what NOT to do)
- Don't label a style without evidence from the tree and the import graph.
- Don't slice work by folder if the dependency direction says the change bleeds across layers — trace it first.
- Don't reverse-engineer the whole import graph by reading every file — sample boundaries with a script.
- Keep concrete package roots out of this skill body — they live in the layer model / inventory leaf.

## Definition of done
- [ ] Architecture style named with the evidence that supports it; modules mapped to responsibilities.
- [ ] Each layer/concern mapped to a package root and a membership naming shape.
- [ ] Dependency direction stated (with any violations) and the per-layer plan split decided.
- [ ] For a pre-slicing pass: the change-path traced to the layers it touches, split into per-layer units.
- [ ] Verified by: every mapping in the written layer model cites a path a reader can open; violations are listed explicitly rather than asserted absent.
