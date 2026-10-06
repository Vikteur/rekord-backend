---
name: capability-mapping
description: Map capabilities to modules and API contract tags. Use when onboarding to fill the capability registers.
---
# Capability mapping

> **Generic "how" only.** Zero project nouns. The concrete capability names, modules, and tags you map
> are written to the capability registers / inventory, referenced below. See `ARCHITECTURE.md` §1 (blueprint repo).

## When to use
On onboarding — when you need the capability ↔ module ↔ contract-tag map that lets the orchestrator
resolve a feature to its modules, tags, and dependencies, and slice the contract by tag.

## How
- **Enumerate the business capabilities** from the module/package names and the API surface, not from
  guesswork — one capability per cohesive feature area.
- **For each capability** record: the module(s) that own it, the layer packages it spans, and the API
  contract tag(s) it relates to — and whether the side *implements* (produces) or *consumes* the tag.
- **Derive the dependency edges** between capabilities (depends-on / depended-by) from cross-module imports.
- **Use the contract tag as the cross-repo join key**: the same tag links a producing module on one
  side to the consuming module(s) on the other, so one side's analyst can point the other at the right place.
- **Flag drift**: code that introduces a capability/tag with no register row (the register is the
  source of truth; missing rows fail the capability-drift gate).
- Cite a defining file (module root, controller, or spec tag) per capability.

## Pattern signals (discovery cues — how the scanner recognizes this in any codebase)
- An API contract (`openapi*.yaml`/`*.json`, `*.proto`, GraphQL SDL) with tags/operations/services.
- Controller/route/resolver classes annotated or grouped by feature; module/package roots named per feature.
- Client-generation config on the consumer side (which tags/operations it pulls).

## Project specifics → see docs
- The discovered map (with provenance) → `docs/_inventory/60-capability-mapper.md`
- The registers it fills → `docs/capability-register.{backend,frontend}.md`, scaffolded from the blueprint repo's `templates/capability-register.*.template.md`

## Guardrails (what NOT to do)
- Don't merge two capabilities because they're adjacent — split on ownership and the contract tag.
- Don't read the whole spec into context; slice it by tag (a script extracts the tagged excerpt).
- Keep concrete capability/module/tag names out of this skill body — they live in the registers / inventory.

## Definition of done
- [ ] Capabilities enumerated, each mapped to its module(s), layer packages, and contract tag(s).
- [ ] Implements-vs-consumes recorded per side; dependency edges derived.
- [ ] Each capability sourced to a defining file; register drift flagged.
- [ ] Verified by: the generated capability register parsing under the resolve-modules script, with every module and tag it names resolving.
