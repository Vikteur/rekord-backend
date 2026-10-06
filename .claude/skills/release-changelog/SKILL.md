---
name: release-changelog
description: Turn Conventional Commits into a reader-facing changelog. Use at release or closeout.
---
# Release Changelog
> **Generic "how" only.** Zero project nouns (no package roots, tag names, version scheme names). Link a docs leaf for any project fact. See `ARCHITECTURE.md` §1 (blueprint repo).

## When to use
At release closeout, once commits since the last tag are known: turning a range of Conventional Commits into the changelog section that ships with a version bump. Pairs with [[conventional-commits]] — the commit shape this reads is that skill's output.

## How
- **Scope to the range** — collect commits since the last release tag; that set is the changelog.
- **Group by type**, reader-facing headings: Features, Fixes, then the rest; drop internal-only types (chore/docs/test/ci) unless user-visible.
- **Headline breaking changes** — a dedicated top section; pull every `!` / `BREAKING CHANGE:` footer up with its migration note.
- **Write for the reader**, not the committer: describe the effect, not the diff; drop scopes/hashes from prose; merge duplicate commits into one entry.
- **Tie to the version bump** — breaking ⇒ major, feat ⇒ minor, fix ⇒ patch; the entries must justify the number chosen.
- **Date and order it** — version + release date header; most impactful first within each group.

## Pattern signals (discovery cues — how the scanner recognizes this in any codebase)
- A CHANGELOG file (Keep-a-Changelog-shaped) with version + date sections.
- Conventional Commit history; annotated release tags; a version field bumped per release.
- A release job/script in CI that assembles notes from the commit range.

## Project specifics → see docs
- Code map (changelog location, versioning scheme, type→section mapping) → `docs/code-maps/release-changelog.md` *(per-repo map, written by the pattern-scanner — resolves once harvested)*

## Guardrails (what NOT to do)
- Don't dump raw commit subjects — a changelog is edited prose, not `git log`.
- Don't bury a breaking change inside Fixes; it gets its own headlined section.
- Don't let the entries contradict the version bump (breaking change under a patch).
- Don't list purely internal churn a user can't observe.

## Definition of done
- [ ] Entries cover exactly the commit range since the last tag, grouped by reader-facing type.
- [ ] Breaking changes headlined up top with migration notes.
- [ ] Prose written for readers; duplicates merged; scopes/hashes stripped.
- [ ] Version header + date present and consistent with the bump the entries justify.
- [ ] Verified by: the entry set diffed against the commit range since the last tag — every reader-facing commit appears once, and nothing appears that is outside the range.
