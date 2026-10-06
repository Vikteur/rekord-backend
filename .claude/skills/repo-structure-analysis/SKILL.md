---
name: repo-structure-analysis
description: Map repos, modules, layout, and branch/ticket/commit conventions. Use when onboarding to fill the profile.
---
# Repo-structure analysis

> **Generic "how" only.** Zero project nouns. The concrete repo names, paths, id patterns, and
> branch conventions you discover are written to the project profile / inventory, referenced below.
> See `ARCHITECTURE.md` §1 (blueprint repo).

## When to use
On onboarding a new project — when you need to know *what the repos are, where the modules live, and
how branches/tickets/commits are named* before any other analyst or the feature pipeline can run.
This is the first analysis pass; everyone downstream needs its module map.

## How
- **Enumerate the repos** and decide mono-repo vs multi-repo: count top-level build roots and VCS
  roots; name each repo's role (app, library, contract hub) and whether it carries a ticket-docs folder.
- **Map the module/package tree** one level deep: list the modules, their directory, and the obvious
  boundary between them. Prefer a script/`ls`/`tree` pass over reading files into context (token rule #4).
- **Recover the conventions from evidence**, not assumption: read VCS history for the branch-name
  shape and commit-message scope; read CI/issue templates for the ticket-id pattern; locate where
  per-ticket docs live.
- **Record each fact with its source path**; where a convention can't be proven from a file, write
  `TODO(verify): <what>` rather than guessing.

## Pattern signals (discovery cues — how the scanner recognizes this in any codebase)
- Build roots / workspace files (`pom.xml`, `build.gradle*`, `package.json`, `go.mod`, `Cargo.toml`,
  `pnpm-workspace.yaml`, `nx.json`, `turbo.json`) — one per module/repo.
- VCS metadata: branch names in history, tag patterns, `CODEOWNERS`, `.github/` issue/PR templates, agent config in `.claude/` (or `.github/` for Copilot).
- A docs or tickets directory whose subfolders are named after issue ids.

## Project specifics → see docs
- The discovered facts (with provenance) → `docs/_inventory/10-repo-structure-analyst.md`
- The completed profile it fills → `docs/project-profile.md`

## Guardrails (what NOT to do)
- Never invent a repo, path, or convention — every line traces to a file you read or is `TODO(verify)`.
- Don't read whole files to count modules; list directories with a script (outside the context window).
- Keep project nouns out of this skill body — they belong only in the inventory / profile leaf.

## Definition of done
- [ ] Every repo enumerated with its role and ticket-docs status.
- [ ] Module/package tree mapped one level deep, each entry sourced to a path.
- [ ] Branch, ticket-id, and commit-scope conventions recovered from evidence (or marked `TODO(verify)`).
- [ ] Verified by: every path in the written profile resolving in the repo, with unrecovered conventions marked TODO(verify) rather than guessed.
