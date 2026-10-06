<!-- Ported to Claude Code from templates/COPILOT-ROOT.template.md in the agentic blueprint (Copilot original: .github/). -->
# Project ground rules for every agent

> This is the **root instruction layer**: Claude Code loads `.claude/CLAUDE.md` at session start, before any
> file is attached. Path-scoped rules under `.claude/rules/` (`paths:` frontmatter) add structural invariants on top
> of it for the code you happen to be editing; they never replace anything here.

## The constitution — non-negotiable (P1–P8)

The supreme law of this framework. Every plan is checked against it, and a deviation is justified in
the plan's `## Complexity Tracking` table — never taken silently.

- **P1 — Lean context is law.** Scope skills per agent and per layer; slice every large artifact
  (plan → per-layer file, spec → tag excerpt, docs → one leaf); one full-reader per artifact; hand
  off summaries, never file dumps.
- **P2 — Determinism over tokens.** Anything a hook or a script can do MUST NOT be done by a model —
  scaffolding, slicing, lint/format, drift checks, codegen, validation.
- **P3 — Generic skills, project docs.** A skill body carries **zero project nouns** (it says *how*);
  every project fact (*what*) lives in a `docs/` leaf. If a skill "needs" a project fact, the leaf is
  missing — add it and link it.
- **P4 — Contract-first.** A contract change lands in the spec and both app repos regenerate (DTOs +
  stubs/client) *before* app code. A red build on regenerated-but-unimplemented stubs is the expected
  starting point, not a failing gate. Never hand-edit generated code.
- **P5 — CI is the source of truth.** No agent runs the test suite locally; a part is done only when
  its CI run is green, fetched by commit SHA. Red ⇒ escalate to the debugger.
- **P6 — Gates are never waived, only reordered or narrowed.** Even an urgent fix keeps branch
  protection and the contract gate. Every workflow ends in a regression test. Recurring human review
  comments become gates.
- **P7 — Architecture invariants hold.** No framework in the domain; dependencies point inward;
  usecase → domain + ports only; adapters hold no business logic. Defended by `arch-fitness`, not by
  reviewer judgment.
- **P8 — Least privilege and declared governance.** Agent and skill manifests are schema-valid; an
  agent that can run commands declares an explicit command allowlist (`Bash(<cmd> *)` in its `tools`,
  enforced by `.claude/hooks/agent-scopes.json` + `scope-guard.sh`); capability and cost are
  auditable, never implicit.

## STOP and get a human decision first

Before anything irreversible or security-bearing: say what you are about to do, why, and what it
would take to undo it — then **wait**. Do not proceed on silence, and do not treat an earlier
"continue" as covering a later one of these; approval is per action, not per session. The list is
short on purpose, because a STOP rule people route around protects nothing:

- **pushing a contract change** to the hub repo, or any spec edit that could break a consumer
  (removed/renamed field or endpoint, narrowed type, new required field, changed status code);
- **a database migration** — schema changes are one-way doors in a production system with real
  personal data, and Flyway will not roll one back for you;
- **authentication, authorization or the access matrix**, SSO/SAML/WS-Security config, or
  anything touching how a user is identified;
- **encryption, key handling, or what gets logged** where personal data could be involved;
- **deleting branches, worktrees, history, or the audit trail**, and any force-push;
- **production configuration**, secrets, and anything that changes what is deployed.

Everything else is ordinary work — do it. This rule exists because none of the above is caught by a
green build: a dropped column and a leaked personal identifier both pass CI.

## How work moves

- **Anything doable via a hook or script must be done that way**, to keep tokens out of the context
  window (branch/folder scaffolding, contract slicing, deterministic gates).
- **Navigate code via the CodeGraph MCP server, not by scanning.** Any agent that reads code uses the
  `codegraph` MCP tools first (exposed in Claude Code as `mcp__codegraph__<tool>`) — `codegraph_explore` (area overview: relevant symbols' source + call
  paths), `codegraph_node` (one symbol / one file), `codegraph_callers` / `codegraph_callees`,
  `codegraph_impact` (blast radius before changing a symbol), `codegraph_search` — instead of
  repo-wide grep or whole-file reads. Same token rule as hooks: pull only the slice you need. Fall
  back to direct reads only when the server or the project's `.codegraph/` index is unavailable, or
  when a CodeGraph staleness banner (⚠️) tells you to read a file directly.
- **Agents hand off via checked-in MD files only** — written into the ticket's docs folder, the
  single home for everything about a ticket.
- **The OpenAPI contract tag is the cross-repo join key** — it links the per-repo capability
  registers and lets one side point the other side's analyst at the right place.
- **One feature branch name, identical across every involved repo** — created (and checked out
  locally) by the start-feature script off the latest `main`.
- **A part is "done" only when its CI run is green** — push the finished part to the open PR
  (`push-on-part`), let CI run the affected tests, and take the run result fetched by **commit SHA**
  (`fetch-ci-result`) as the answer. Never trust a local "looks green" judgment.
- **Report what the tree shows, not what you intended.** A completion claim is checked against the
  work tree by `verify-claims`, and enforced on the PR by CI.
- **Docs cross-reference docs with shortcut reference links** — `[label]` inline, `[label]:
  relative/path.md` definitions collected at file bottom. Plain backticked paths only where the
  target doesn't resolve in the repo (blueprint paths, placeholders) — and in **skill/instruction
  bodies**, which keep plain paths so harness auto-attach can't eager-load the leaf.

## Project specifics → see docs

- Ticket id, branch name, ticket docs folder, repo names → `docs/project-profile.md`
- The OpenAPI-tag join key & per-repo sync → `docs/layer-model.md`
- What is regulated here, and why → `docs/code-maps/security-review.md`
  *(plain references on purpose — linked files eager-load into every context; open them on demand)*
- Decisions already taken, and approaches already tried and abandoned → `docs/memory.md` — read it
  before proposing a change that reverses one; the reasoning is not in the code
- Paths under `templates/`, `knowledge/`, `workflows/`, `archive/`, `migration/`, and
  `ARCHITECTURE.md` refer to the **blueprint repo** (`<org>/agentic-blueprint`) — they are
  not vendored into consumer repos.

## Shared mechanisms (not agents, but everyone must respect them)

- **Gates** — deterministic checks that can fail a step (e.g. `declared-files-disjoint`).
- **Hooks** — deterministic guardrails between WORKFLOW → SKILLS → DOCS. In-loop `SubagentStop`
  gates **report**; the PR's CI is what blocks. Treat an advisory failure as a real one anyway.
- **Worktrees** — each agent instance works in its own clean worktree; never collide.

