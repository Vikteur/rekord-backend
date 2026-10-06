---
name: clean-architecture
description: Keep dependencies pointing inward — domain, use-cases, adapters. Use when placing or slicing code across layers.
---
# Clean Architecture

> **Generic "how" only.** Zero project nouns. The concrete layer set, package roots and module map
> live in the code-map / `docs/layer-model.md`, referenced below. See `ARCHITECTURE.md` §1 (blueprint repo).

## When to use
Placing new code in a layer, slicing a feature across layers, or reviewing dependency direction.
The one shared structural skill every code-writing agent (and the analyst) carries. It decides *where*
code goes; how the unit itself is written is [[clean-code]].

## How
- Concentric layers; **dependencies point inward only.** Inner layers know nothing of outer ones.
- **Domain** (core): entities, value objects, invariants, domain events. No framework, no I/O.
- **Use-cases** (application): orchestrate domain + ports; hold application logic and transaction
  boundaries. Depend on domain + port *interfaces*, never on adapter implementations.
- **Adapters** (edge): controllers, gateways, persistence. Map the outside world ↔ use-cases; no
  business logic. Ports are interfaces owned by the inside, implemented at the edge.
- Cross a boundary only through a port; invert the dependency when the arrow would point outward.

## Pattern signals (discovery cues — how the scanner recognizes this in any codebase)
- Directory/package split resembling `domain` / `usecase|application` / `adapter|infrastructure`.
- Interfaces (ports) in inner packages implemented in outer ones (dependency inversion).
- Inner packages with no framework imports; framework/IO confined to the edge.
- Architecture-fitness tests present (e.g. ArchUnit) asserting dependency direction.

## Project specifics → see docs
- Code map (layer→package mapping, module list, exemplars) → `docs/code-maps/clean-architecture.md` *(per-repo map, written by the pattern-scanner — resolves once harvested)*
- The project's layer set & per-layer plan files → `docs/layer-model.md`

## Guardrails (what NOT to do)
- Don't import a framework or adapter type from the domain (hook: archunit/dependency gate).
- Don't put business rules in a controller or gateway.
- Don't let a use-case depend on a concrete adapter — depend on the port.

## Definition of done
- [ ] New code sits in the correct layer; dependencies point inward.
- [ ] Boundaries crossed only via ports; no outward imports.
- [ ] Architecture-fitness checks pass.
- [ ] Verified by: the arch-fitness suite green on the part's CI run — not by reading the imports.
