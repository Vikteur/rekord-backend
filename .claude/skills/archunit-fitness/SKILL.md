---
name: archunit-fitness
description: Encode architecture rules as ArchUnit fitness tests. Use for the post-part arch checks.
---
# ArchUnit Fitness

> **Generic "how" only.** Zero project nouns. The concrete package roots, allowed libraries and
> exemplars live in the code-map docs leaf, referenced below. See `ARCHITECTURE.md` §1 (blueprint repo).

## When to use
Authoring or maintaining the **architecture-fitness suite** — the executable rules that the
**post-part hook** runs after a developer/test-writer finishes (so a layering violation fails the
part deterministically, not by reviewer judgment). The test-writer owns these standing rules per
layer.

## How
- Write rules as code (ArchUnit) that assert structure, not behavior; keep them in a fast suite that
  needs **no application context** (no Spring boot) so it can run as a post-part hook.
- Encode the non-negotiables:
  - **No framework in the domain** — domain classes depend on no web/persistence/DI/framework
    packages (no Spring, JPA/jakarta, HTTP, I/O).
  - **Dependency direction is inward** — domain depends on nothing outward; usecase depends only on
    domain + port interfaces; adapters depend inward, never the reverse.
  - **Layer purity** — controllers/gateways hold no business logic; domain invariants live in the
    domain; ports are interfaces owned by the inside, implemented at the edge.
- Make each rule **fail with a clear message** (which class broke which rule) so the post-part hook's
  output points straight at the fix.
- One rule per invariant; freeze a baseline only for documented, tracked exceptions.

## Pattern signals (discovery cues — how the scanner recognizes this in any codebase)
- ArchUnit on the test path (`com.tngtech.archunit`), `@AnalyzeClasses`, `ArchRule`/`classes()...`.
- A dedicated fast fitness/architecture test source set separate from unit/integration tests.
- `layeredArchitecture()`, `noClasses().that().resideInAPackage("..domain..")` style rules.

## Project specifics → see docs
- Code map (package roots per layer, allowed libs, baselined exceptions, exemplars) → `docs/code-maps/archunit-fitness.md` *(per-repo map, written by the pattern-scanner — resolves once harvested)*

## Guardrails (what NOT to do)
- Don't assert runtime behavior here — fitness rules are static structure (keep them boot-free/fast).
- Don't weaken a rule to make a part pass; if an exception is real, baseline it explicitly and track it.
- Don't duplicate what the path-scoped rules (`.claude/rules/*.md`) say as prose — here it is *executable*.

## Definition of done
- [ ] Each layer invariant has an executable rule with a clear failure message.
- [ ] The suite runs without an application context (fast enough for a post-part hook).
- [ ] Green for the part; any exception is baselined and tracked, not silently allowed.
