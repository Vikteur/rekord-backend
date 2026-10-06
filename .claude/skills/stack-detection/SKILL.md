---
name: stack-detection
description: Identify languages, frameworks, runtimes, and build tooling from manifests. Use when onboarding.
---
# Stack detection

> **Generic "how" only.** Zero project nouns. The concrete languages, framework names, and versions
> you detect are written to the inventory / code-maps config, referenced below. See `ARCHITECTURE.md` §1 (blueprint repo).

## When to use
On onboarding — when you need the project's tech stack (languages, frameworks, build tooling) to wire
the side-language skills and set the languages-in-scope for later pattern scanning.

## How
- **Read the manifests, not the source**: dependency and lockfiles name the languages, frameworks, and
  their versions far more reliably than scanning code. Start there.
- **Per side/module**, record: primary language(s) + version, the framework(s) and major version, the
  runtime/target, the package manager, and the build tool.
- **Distinguish runtime from dev/test dependencies** so the testing analyst gets a clean handoff.
- **Pin versions from lockfiles** where present; if only a range is declared, record the range and mark
  the resolved version `TODO(verify)`.
- **Map the languages in scope** for the code-maps config (which file globs the pattern-scanner should
  later scan).
- Cite the manifest path for every fact.

## Pattern signals (discovery cues — how the scanner recognizes this in any codebase)
- Manifest/lockfiles: `package.json`+`package-lock.json`/`pnpm-lock.yaml`/`yarn.lock`, `pom.xml`,
  `build.gradle*`+`gradle.lockfile`, `requirements.txt`/`pyproject.toml`/`poetry.lock`, `go.mod`/`go.sum`,
  `Cargo.toml`/`Cargo.lock`, `*.csproj`, `Gemfile.lock`, `composer.lock`.
- Framework markers in deps (web frameworks, ORMs, UI frameworks) and engine/runtime fields.
- Toolchain config: `.nvmrc`, `.tool-versions`, `Dockerfile` base images, CI setup steps.

## Project specifics → see docs
- The detected stack (with provenance) → `docs/_inventory/30-stack-analyst.md`
- Languages-in-scope for scanning → `docs/code-maps/README.md`

## Guardrails (what NOT to do)
- Don't infer a framework from a single import when a manifest states it — manifests win.
- Don't report a version you can't source to a manifest/lockfile; mark it `TODO(verify)`.
- Keep concrete framework/version values out of this skill body — they live in the inventory leaf.

## Definition of done
- [ ] Each side/module's language(s), framework(s), runtime, package manager, and build tool recorded.
- [ ] Versions pinned from lockfiles (or ranges noted with `TODO(verify)`), each sourced to a manifest.
- [ ] Languages-in-scope set for the code-maps config.
