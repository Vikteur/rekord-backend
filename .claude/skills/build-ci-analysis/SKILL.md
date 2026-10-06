---
name: build-ci-analysis
description: Detect build commands, CI stages, and enforced gates. Use when onboarding to record build and CI.
---
# Build/CI analysis

> **Generic "how" only.** Zero project nouns. The concrete commands, pipeline jobs, and gate names you
> find are written to the inventory / workflow config, referenced below. See `ARCHITECTURE.md` §1 (blueprint repo).

## When to use
On onboarding — when you need the project's build commands, CI stages, and the gates CI enforces, to
fill the workflow config and reconcile the gate catalog with reality.

## How
- **Recover the build/test/lint commands** per side from the build tool config and scripts block — the
  exact invocations a developer or CI runs.
- **Read the CI pipeline** and list its stages in order, what each runs, and what triggers it.
- **Extract the enforced gates**: which checks block a merge (tests, lint/format, coverage threshold,
  arch-fitness, commit-message format, branch protections, required reviews).
- **Map each enforced gate to the framework's gate catalog**: matched (already named), or a candidate
  gate to add. Note anything done by hand that *should* be a gate (token rule #4: mechanical → hook).
- **Note the contract/regeneration steps** in CI if the project has a spec seam.
- Cite the pipeline/config path for every command and gate.

## Pattern signals (discovery cues — how the scanner recognizes this in any codebase)
- CI definitions: `.github/workflows/*.yml`, `.gitlab-ci.yml`, `azure-pipelines.yml`, `Jenkinsfile`,
  `.circleci/config.yml`, `bitbucket-pipelines.yml`.
- Build/script entry points: `scripts`/`tasks` blocks in `package.json`, Gradle/Maven goals, `Makefile`,
  `justfile`, `Taskfile.yml`.
- Gate config: lint/format configs, coverage thresholds, branch-protection/required-check settings,
  commit-lint, pre-commit hooks.

## Project specifics → see docs
- The discovered facts (with provenance) → `docs/_inventory/50-build-ci-analyst.md`
- The workflow config it fills → `docs/workflow.new-feature.md`
- The gate catalog to reconcile → `templates/hooks-and-gates.md` (blueprint repo)

## Guardrails (what NOT to do)
- Don't list a command you can't source to a config file; mark unverified invocations `TODO(verify)`.
- Don't treat a non-blocking job as a gate — a gate is a check that *blocks*.
- Keep concrete commands/job names out of this skill body — they live in the inventory / workflow leaf.

## Definition of done
- [ ] Build/test/lint commands recovered per side, each sourced to config.
- [ ] CI stages listed in order with their triggers.
- [ ] Enforced gates extracted and reconciled to the gate catalog (matched / candidate / manual-to-automate).
