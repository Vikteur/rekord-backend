---
name: contract-apply-pr
description: Land an API-contract change as a reviewable PR — branch, lint, compat diff. Use when shipping a contract change.
---
# Contract apply PR
> **Generic "how" only.** Zero project nouns (no spec filenames, repo names, tag names, branch prefixes, consumer/package roots). Link a docs leaf for any project fact. See `ARCHITECTURE.md` §1 (blueprint repo).

## When to use
Turning an approved contract change into a merged PR against the spec-as-contract repo: you have the operation/schema delta and need to branch, edit the spec, gate it, and land it so downstream consumers can regenerate. Mechanical apply, not authoring judgment.

## How
- **Work on a branch** off the current baseline; one contract change per branch/PR. If the
  pipeline's scaffolding already created the branch, use that one — never create a second.
- **Make the edit additive** — new operation, optional field, added enum value; never repurpose or remove existing shape in the same change.
- **Lint the spec** with the repo's ruleset; fix all violations before pushing.
- **Diff against the published baseline** with the breaking-change checker; the diff must come back additive-only, else split or redesign.
- **Land it as a PR** whose summary states the operation/schema delta explicitly — what was added, why, and that it is backward-compatible; attach the lint + diff output. Where the pipeline centralizes PR creation in an orchestrating role, hand off for it to open the PR instead of opening it yourself — the summary content is this skill's concern either way.
- **Coordinate consumers**: consumers regenerate clients/stubs from the *merged* spec, not the branch — call out who regenerates and in what order.

## Pattern signals (discovery cues — how the scanner recognizes this in any codebase)
- A spec document tracked as the canonical contract; a lint config beside it.
- CI that runs lint + a breaking-change diff on PRs; a published baseline/tag to diff against.
- Generated client/stub packages that consume the spec (regen job or codegen config).

## Project specifics → see docs
- Code map (spec location, lint/diff commands, baseline ref, consumer regen order) → `docs/code-maps/contract-apply-pr.md` *(per-repo map, written by the pattern-scanner — resolves once harvested)*

## Guardrails (what NOT to do)
- Don't merge a change whose breaking-change diff is non-additive — split it or version it.
- Don't hand-edit generated client/stub code to match the spec; regenerate from the merged contract.
- Don't bundle unrelated deltas into one PR — a reviewer must see one coherent contract change.
- Don't push before lint and the breaking-change diff both pass locally.

## Definition of done
- [ ] On a branch off baseline (existing or new, per the pipeline's ownership); single additive delta; lints clean.
- [ ] Breaking-change diff vs published baseline is additive-only.
- [ ] PR opened — by whichever role owns PR creation — with an explicit operation/schema-delta summary + lint/diff output.
- [ ] Consumer regeneration sequenced off the merged spec.
