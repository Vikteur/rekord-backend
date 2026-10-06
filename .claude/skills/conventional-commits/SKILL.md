---
name: conventional-commits
description: Write Conventional Commits so changelog and version bumps derive. Use when committing.
---
# Conventional Commits
> **Generic "how" only.** Zero project nouns (no scope vocabulary, tag names, package roots, release-tool names). The allowed scopes and any local overrides live in a docs leaf, referenced below. See `ARCHITECTURE.md` §1 (blueprint repo).

## When to use
Writing any commit message on a project where history, changelog, and version bumps are derived from commits. Applies per commit, before it lands.

## How
- **Shape every subject** as `type(scope): summary` — scope optional, summary in imperative mood, lower-case, no trailing period.
- **Pick the type** from the agreed set: `feat`, `fix`, `refactor`, `docs`, `test`, `chore`, `build` (feat/fix drive the version bump).
- **One logical change per commit** — split unrelated edits so each maps to a single type and a single changelog line.
- **Flag incompatible changes** with a `BREAKING CHANGE:` footer (or `!` after the type/scope); this forces the major bump.
- **Keep the body optional but useful** — explain *why*, reference issues in footers, wrap prose sensibly.

## Pattern signals (discovery cues — how the scanner recognizes this in any codebase)
- A commit-lint config or commit-msg hook enforcing the type/scope grammar.
- A generated CHANGELOG and an automated version-bump / release job in CI.
- History where subjects consistently start with `feat`/`fix`/`chore` prefixes.

## Project specifics → see docs
- Code map (allowed scopes, type set overrides, changelog config) → `docs/code-maps/conventional-commits.md` *(per-repo map, written by the pattern-scanner — resolves once harvested)*

## Guardrails (what NOT to do)
- Don't bundle unrelated changes in one commit — it breaks the one-line-per-change changelog and muddies the bump.
- Don't invent types outside the agreed set; an unknown type is dropped from the changelog or fails commit-lint.
- Don't bury an incompatible change without a `BREAKING CHANGE:` footer — the major bump won't derive.
- Don't write past-tense or capitalized subjects; keep the imperative, lower-case grammar the tooling parses.

## Definition of done
- [ ] Subject is `type(scope): summary`, imperative, from the agreed type set.
- [ ] Commit is one logical change; incompatible changes carry a `BREAKING CHANGE:` footer.
- [ ] Message passes commit-lint / the commit-msg hook and yields a clean changelog line.
