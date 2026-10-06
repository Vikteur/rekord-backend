---
name: cross-repo-orchestration
description: Coordinate one contract change across repos, producer before dependents. Use for multi-repo changes.
---
# Cross-repo orchestration
> **Generic "how" only.** Zero project nouns (no repo names, contract filenames, generator commands, branch prefixes). Link a docs leaf for any project fact. See `ARCHITECTURE.md` §1 (blueprint repo).

## When to use
One logical change spans two or more repositories coupled through a shared contract, and the repos must stay in sync. Not for a change contained in a single repo, or repos with no shared seam.

## How
- **Contract-first**: land the shared-contract change before touching any consumer; it is the single seam every repo aligns to.
- **Order by dependency**: producer of the contract before its consumers; a consumer that others depend on before the leaves.
- **Regenerate, don't hand-edit**: each consumer re-derives its bindings from the new contract (codegen / regenerate), then adapts call sites.
- **One seam only**: route all cross-repo coupling through the contract — no repo reaching into another's internals to compensate.
- **Track the fan-out**: enumerate every consumer up front; check each off as it lands so none is left un-synced. Link the PRs so the set is reviewable together.
- **Sequence the merge** so no consumer ships against a contract version that isn't published yet.

## Pattern signals (discovery cues — how the scanner recognizes this in any codebase)
- A dedicated contract/schema repo consumed by others (generated-client dirs, pinned contract version).
- Multiple repos referencing the same spec artifact; codegen steps in more than one build.
- Cross-repo PR links / a coordinating checklist or tracking issue.

## Project specifics → see docs
- Code map (repos, contract location, codegen commands, merge order) → `docs/code-maps/cross-repo-orchestration.md` *(per-repo map, written by the pattern-scanner — resolves once harvested)*

## Guardrails (what NOT to do)
- Don't change a consumer ahead of the contract it depends on — the contract lands first, always.
- Don't hand-patch generated bindings to dodge a regenerate step; fix the contract and re-derive.
- Don't merge a consumer against an unpublished contract version, or leave any enumerated consumer un-synced.

## Definition of done
- [ ] Contract change landed and published first; consumers ordered producer-before-dependents.
- [ ] Every consumer regenerated from the contract and adapted; fan-out list all checked off.
- [ ] No out-of-band coupling added; merge order leaves no repo pinned to a missing version.
- [ ] Verified by: every repo in the fan-out having a green CI run on the merged contract version, fetched by commit SHA.
