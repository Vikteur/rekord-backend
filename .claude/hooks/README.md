# `.claude/hooks` — Claude Code hooks: observability, governance, gates

> **Claude Code port.** This folder was ported from a Copilot CLI setup (`.github/hooks/`). What
> changed:
>
> - **Wiring.** All hooks are registered in **`.claude/settings.json`** (`hooks` key). The Copilot
>   files `observability.json`, `governance.json` and `gates.json` no longer exist; the sections
>   below still use those names for the three *groups* of hooks.
> - **Event mapping.** `sessionStart` → `SessionStart` · `userPromptSubmitted` → `UserPromptSubmit` ·
>   `preToolUse` → `PreToolUse` (matcher `Write|Edit|MultiEdit|NotebookEdit|Bash`) ·
>   `postToolUse[Failure]` → `PostToolUse[Failure]` · `subagentStart/Stop` → `SubagentStart/Stop` ·
>   `sessionEnd` → `SessionEnd`. Each script still receives the original camelCase event name as `$1`.
> - **Commands.** Commands run `cd "$CLAUDE_PROJECT_DIR/.claude/hooks" && exec bash scripts/<x>.sh`.
>   `timeoutSec` became `timeout`, still in seconds.
> - **"allow" is not neutral in Claude Code.** `permissionDecision:"allow"` skips the user's
>   permission prompt, so a guard with no objection exits 0 with **no output**. Only `deny` is emitted.
> - **New per-agent fence.** `scripts/scope-guard.sh` (PreToolUse) enforces `agent-scopes.json`, the
>   per-agent `allowedFilePaths` / `commandAllowlist` the Copilot agents declared in frontmatter.
>   It keys off the `agent_type` field that Claude Code puts on every event inside a subagent.
> - **Gates are advisory.** A `SubagentStop` hook that exits 1 is reported, not enforced. Exit **2**
>   would make the subagent keep working; switch a gate to exit 2 only if you want it to block.
> - **Environment variables.** The `COPILOT_*` variables are now `CLAUDE_*`: `CLAUDE_GUARD_ALLOW_HOOK_EDITS`,
>   `CLAUDE_AUDIT_ROLE`, `CLAUDE_AUDIT_TICKET`, `CLAUDE_AUDIT_PROMPTS`. The old names are still honoured.
> - **Measurements.** Probe results below marked *Copilot CLI 1.0.78* are history from the original
>   harness, kept for the reasoning.

The hooks in `.claude/settings.json` run the named script at each lifecycle event. This folder wires
the **audit trail**: no single file answers "which skill did
which agent use in this workflow run?" — three records do, and you cross-reference them:

| Record | Answers | Where |
|---|---|---|
| **Lockfile** | *what was available, at which version* | `apm.lock.yaml` per commit (deployed set + `generated_at`); git history is the time machine — each `SKILL.md`'s version is its last-touch commit |
| **Harness load log** | *what actually bound, when* | `.apm-audit/sessions/<sessionId>.jsonl` — every session/tool/subagent event with timestamps, in three tiers: `SCOPE` (what the checkout offered), `*_SEEN` (surfaced in a tool result — discovered), `*_LOAD` (explicitly opened — read & used, with the acting agent + the file's commit at that moment) |
| **Persisted plans** | *who ran, what they did* | the ticket's `docs/{epic}/{ticket}/` artefacts (handoff, plans, debug, retro) plus the rendered `skill-usage.md` report committed with the PR |

**The join:** session id × commit/lockfile × load log = which agent loaded which skill, at which
version, when. `scripts/audit-report.sh` performs it (`--ticket PROJ-123 --write docs/…/skill-usage.md`)
and renders **one table per agent** with three columns: *scoped into worktree* (its `SCOPE`) ·
*discovered* (`*_SEEN` ∪ `*_LOAD`) · *read & used* (`*_LOAD`, with load count + last-touch commit).

> **Shell: Git Bash (bash), minimum bash 3.2.** Hooks are wired through the JSON `bash` key, so they
> run in Git Bash on Windows and bash elsewhere. **3.2 is the floor because macOS still ships it as
> `/bin/bash`**, and `#!/usr/bin/env bash` picks that up on any machine without a newer bash on PATH.
> A bash-4-only construct doesn't degrade — the script dies before printing a decision, and a hook
> with no parseable decision fails *open*, so one expansion can silently disable a whole governance
> hook on a subset of workstations. The blueprint repo's CI (`ci.yml`) gates the common bash-4-isms — the
> case-conversion expansions (`${x,}`, `${x,,}`, `${x^}`, `${x^^}`), `mapfile`/`readarray`, and
> `declare`/`local -A` — and self-tests its own pattern against a probe. Prefer `shopt -s nocasematch`
> and friends. A green gate is **not** a compatibility proof: `coproc`, `|&` and `&>>` are 4+ too, and
> no grep can tell you whether the semantics a script relies on exist in 3.2.
> `jq` is optional but recommended — without it the args/result split is impossible, so every path
> mention counts as a `*_LOAD` (discovery folds into usage).

## What's wired (`observability.json`)

| Event | Effect |
|---|---|
| `sessionStart` | Opens the session record (role/ticket from `scripts/run-role.sh` env, HEAD SHA, branch, `apm.lock.yaml` stamp) + a `SCOPE` record: the deployed `.github/skills/` + `.github/instructions/` this checkout offers — the report's "scoped into worktree" column |
| `userPromptSubmitted` | Logs the prompt (truncated to 200 chars) |
| `postToolUse` / `postToolUseFailure` | Logs the tool call, then splits observation: a `skills/<name>/SKILL.md` or `*.instructions.md` path in the tool **args** is an explicit open → `SKILL_LOAD` / `INSTRUCTION_LOAD` (read & used, version-stamped — `view` or a shell `cat` alike); a path only in the tool **result** (an `ls`/grep/search that scrolled past) → `SKILL_SEEN` / `INSTRUCTION_SEEN` (discovered). `agents/<role>.agent.md` reads → `PERSONA_LOAD` |
| `subagentStart` / `subagentStop` | Logs the subagent + maintains the attribution stack (`agentName` is only present on these events, so tool calls in between are attributed to the top of the stack) |
| `sessionEnd` | Closes the record with the stop reason |

All hooks call one script, `scripts/audit-log.sh <event>`. It **always exits 0** and is wired to
`postToolUse` (not fail-closed `preToolUse`) on purpose: observability must never deny or delay a
tool call. Raw logs land in `.apm-audit/` (gitignored — **verify this in each consumer**; the entry
lives in the consumer's own `.gitignore`, which no sync writes, and one consumer ran for months without
it while this line claimed otherwise); only rendered reports get committed.

Two properties this trail is expected to have, and their real state:

- **It does not store prompt text.** `audit-log.sh` records a truncated SHA-256 and a character
  count, not the prompt. A prompt is the least predictable field in the trail — in practice it has
  carried ticket context, pasted logs and credential hints — and nothing consumes it
  (`scripts/audit-report.sh` never reads it). The hash still answers "same prompt or not", which is
  the only thing a reconstruction asks. `COPILOT_AUDIT_PROMPTS=raw` restores verbatim capture for one
  session; it is an env var and deliberately not a `hooks.env` key, so opting into storing user text
  stays a per-session act by a human rather than a repo setting that drifts.
- **An agent cannot delete it.** `guard-generated.sh` rule 1b denies a shell command that names
  `.apm-audit` alongside a destructive verb, and denies `git clean -x`/`-X` — which takes the trail
  out without ever naming it, because the trail is an ignored file. Reads, greps and appends are
  untouched. Residual: this sees a tool call's command string, not a script the agent wrote and then
  ran.
- **It is still local and ephemeral.** Nothing ships these files off the workstation, so the trail
  dies with the machine and cannot be used as evidence after the fact. Closing that is a deployment
  decision (a durable sink), not a hook change — until it is made, treat `.apm-audit/` as local
  debugging output that is *safe to keep*, not as an audit record you can produce later.

## Governance hooks (fail-closed) — `governance.json`

`observability.json` only *watches* (`postToolUse`, always exit 0). A **governance** config instead
*gates*: a `preToolUse` hook that can **DENY** a tool call. `governance.json` wires
`scripts/guard-generated.sh`, which denies a `Write`/`Edit` under **two** rules:

| Rule | Owner | Where | What |
|---|---|---|---|
| generated paths | consumer | `guard-generated.globs` | per-repo opt-in, ships empty — enforces constitution **P4** (regenerate from the OpenAPI contract, never hand-edit) |
| `.github/hooks/*` | framework | built into `guard-generated.sh` | self-protection: `hooks.env` and the gate scripts execute automatically at a lifecycle boundary, so an agent that can rewrite them has command execution |

The second is hard-coded rather than shipped as a glob **because the two have opposite update
policies**: the globs file is consumer-owned, so an upgrade must not overwrite it — a framework rule
living there would never reach any repo that already had the file, which is every existing consumer.
It also runs *before* the "no globs file → allow" check, so the opt-in default still gets it. Hook
edits are a human operation; when authoring hooks *is* the session's job (this repo), launch it with
`COPILOT_GUARD_ALLOW_HOOK_EDITS=1`. Both rules gate `Write`/`Edit`, not a `bash` call with a
redirect. The
decision is the JSON `permissionDecision` field, not the exit code; like every hook it fails **open**
on a parse error / missing `jq` / missing config, so it can never stall or break a session. CI
smoke-tests the deny/allow/opt-in logic (the blueprint repo's `ci.yml`).

## Gate hooks (advisory) — `gates.json`

`observability.json` *watches* (always exit 0) and `governance.json` *gates a tool call* (`preToolUse`
deny — the one hook whose verdict the CLI actually enforces). A third category *inspects a part*:
`gates.json` wires `subagentStop` scripts that run the repo's deterministic quality checks the moment
a code-writing subagent finishes.

**These were designed as fail-closed gates and are not.** The probe recorded below measured it: on
Copilot CLI 1.0.78 a non-zero `subagentStop` exit is written to the session transcript as
`success: false` and then **discarded** — the part is accepted, the delegating session continues,
the run completes normally. So treat what follows as *advisory*: the scripts run, they log, and they
tell a human precisely what is wrong, but nothing in the harness stops a bad part on their verdict.
Enforcement lives in CI on the PR. They are still worth running — an in-loop signal minutes after the
mistake beats one on a PR an hour later — but do not build a control whose only enforcement point is
here, and do not describe them as blocking:

| Script | Gate | Command (per-repo `hooks.env`) |
|---|---|---|
| `scripts/arch-fitness.sh` | layer purity | `ARCH_FITNESS_CMD` runs the boot-free ArchUnit / dependency-cruiser check |
| `scripts/verify-claims.sh` | self-report verification | no command — reads the work tree directly (optional `VERIFY_CLAIMS_BASE` / `VERIFY_CLAIMS_DECLARED`) |

**`scripts/lint-format.sh` ships but is deliberately NOT wired in `gates.json`.** It spent its first
releases in the worst possible state: registered as a blocking gate, listed in every review of this
setup as one of three enforcement points, and `exit 0` on every single run because no consumer had
ever set `LINT_FIX_CMD`. A gate that always passes is worse than no gate — it buys false confidence
in everything downstream of it, and the cost is paid by whoever later assumes formatting was checked.
The script is kept because it is correct and a consumer with a real formatter task should use it: add
its entry back to `gates.json` **in the same change** that sets `LINT_FIX_CMD` / `LINT_CHECK_CMD` in
`hooks.env`, never before. Registering the hook is the last step, not the first.

Both wired gates are **boot-free and fast** — they run on the workstation even though the heavy test
suite is offloaded to CI. Three things about them are load-bearing:

- **Which agents they fire for.** `subagentStop` fires for *every* subagent, so both scripts read
  `agentName` off the payload (via `scripts/gate-common.sh`) and run only for the roles that write
  code — `GATE_AGENTS`, default `developer test-writer contract-agent`. `analyst`, `reviewer`,
  `design-critic`, `retro` … skip instead of paying a formatter + fitness run for code they never
  wrote. An **absent or unparseable** `agentName` (no `jq`, garbled payload) *runs* the gate: unknown
  identity must not be a way past a fail-closed check. Same direction everywhere else — no git work
  tree, or a failed `cd` to the root, exits **non-zero** rather than silently reporting success.
- **`verify-claims` is the one gate with nothing to configure.** The other two are inert until a repo
  supplies a command, which is exactly how `arch-fitness` and `lint-format` spent their first release
  doing nothing. `verify-claims` needs no command because its check is not a build step: it compares
  the agent's *claim* of completion against `git status` + `git diff <base>...HEAD`, and an empty
  result with a "done" claim is a hallucinated edit no matter what stack the repo is. It is the only
  thing in this system that reads the work tree rather than the agent's summary — every other check,
  including the reviewer, is downstream of the unverified premise that the writes landed. Its second
  half (did the change land inside the part's **Declared Files**) does need `VERIFY_CLAIMS_DECLARED`,
  and says on every run when it is skipping for want of it, because a silent skip is indistinguishable
  from a pass. Degraded paths — unresolvable base, missing plan file, detached HEAD — fail **open**
  with a printed reason: "this gate cannot tell" is not evidence of a bad agent, and a gate that
  bounces honest work gets deleted within a day.
- **`hooks.env` is parsed, never sourced — and is still code.** Only `KEY=value` lines for
  `LINT_FIX_CMD` / `LINT_CHECK_CMD` / `ARCH_FITNESS_CMD` / `GATE_AGENTS` / `VERIFY_CLAIMS_BASE` /
  `VERIFY_CLAIMS_DECLARED` are honoured; anything else
  (unknown key, or no `=`) is reported and skipped. Be precise about what that buys: the three `*_CMD` values
  are `bash -c`'d by the gates, so a `hooks.env` containing `ARCH_FITNESS_CMD="touch PWNED"` still
  runs it. Parsing removes *incidental* execution and shrinks the shape from "arbitrary shell anywhere
  in the file" to "one command in one of three values" — it does **not** make a writable `hooks.env`
  safe. That is why `guard-generated.sh` has a built-in deny on `.github/hooks/*` (see the governance
  section), and even that gates an agent's `Write`/`Edit` and not a `bash` redirect. Treat it as code.
  Precedence is **first wins and announced**: an exported value beats the file, an earlier line beats
  a later duplicate, and the gate says which it used on its `running:` line — a stale exported
  `ARCH_FITNESS_CMD` otherwise looks exactly like a parser bug.
  The framework ships `hooks.env` **real but fully commented out** (same mechanism as
  `guard-generated.globs`, so it travels with `build/hooks/` and needs no copy step); with nothing
  uncommented each gate is an informative no-op.
- **There is no CI backstop for `arch-fitness` in the consumer state.** (`lint-format` is unwired —
  see above; a consumer that re-wires it must set `LINT_CHECK_CMD` too, not just `LINT_FIX_CMD`, or
  the hook is a silent auto-format rather than a gate.) `arch-fitness` is
  in the same position: it used to be doubled by `agentic-quality.yml → archTest`, but the migration
  removes that workflow from consumers (the blueprint repo's `migration/README.md`) and its
  replacement — `agentic-gates.yml`, templated from the blueprint's `migration/consumer-ci/` and
  deployed as the consumer's `.github/workflows/agentic-gates.yml` — runs no `archTest`. Until a consumer wires a fitness step
  into its own build CI, this hook is the only thing checking layer purity there — and it no-ops
  entirely while `ARCH_FITNESS_CMD` is unset.

  **The inverse is the trap, and it has been hit.** Where the fitness suite is written as ordinary
  tests, the consumer's normal `test` task already runs it, so `./gradlew clean build` fails on the
  same rules in CI — and CI *blocks*, while this hook provably cannot. Uncommenting
  `ARCH_FITNESS_CMD` there buys nothing and costs a full compile-and-run on every code-writing
  subagent stop: measured at ten invocations in one ticket, each with a 600s budget, every verdict
  discarded. One backend consumer did exactly this — its `application/build.gradle.kts` says
  outright that "`test` still runs these as part of the full suite; archTest is a focused entry
  point, not a replacement" — and paid for it on every part.

  So the decision is per consumer and it is a real decision: **check whether your build CI already
  covers the rules before you uncomment the key.** Where it does, leave it commented and let CI be
  the gate. Where it does not, uncomment it and read its output as advice, not as a bounce.

These scripts **can** exit non-zero — the observability rule ("always exit 0") does not apply to them,
though per the probe below the CLI currently records that non-zero rather than acting on it.
CI smoke-tests both directions (no-op when unconfigured, non-zero when the underlying check fails,
skip for a non-code-writing agent) in the blueprint repo's `ci.yml`.

## The hook contract (Copilot CLI)

- Each hook gets a JSON payload on **stdin**: `sessionId`, `timestamp`, `cwd`, plus per event
  `toolName`/`toolArgs` (`postToolUse*`), `agentName`/`transcriptPath` (`subagentStart`/`Stop`),
  `prompt`, `reason`. camelCase from the CLI; snake_case tolerated (cloud agent PascalCase configs).
- Main-session attribution: `preToolUse`/`postToolUse` carry **no agent identity**. The launcher
  (`scripts/run-role.sh <role>`) exports `COPILOT_AUDIT_ROLE`, which the CLI process — and thus
  every hook it spawns — inherits. A bare `copilot` session still logs, attributed to `main`.
- Known gap: the built-in `general-purpose` subagent emits no `subagentStart`/`Stop`, and parallel
  subagents interleave the stack — the raw `AGENT_START`/`STOP` records keep that visible.
- Record shape, on those two specifically: `agent` is *who was acting*, resolved after the stack is
  updated, so it reads `developer` on `AGENT_START` but the **parent** (`main`) on `AGENT_STOP`; the
  stopping subagent is always in `agentName`. Deliberate — that ordering is what attributes the next
  `postToolUse` to the parent — and harmless to the report, which never reads `agent` on `AGENT_*`
  (`scripts/audit-report.sh` filters it against `ACTIVE`, which excludes both). It matters only if you
  query the raw trail: key off `type` + `agentName`, never `agent`. See the timeout-probe note below,
  where getting this wrong flips the conclusion.
- **Timeouts and failures — MEASURED, see the answer below.** (Historic note: this was an open question, and the design assumed the wrong answer.) What the CLI does when a hook exceeds its
  timeout — treat it as a non-zero exit, or drop the hook's verdict — is *not* something we have
  pinned down against the CLI, and for a fail-closed gate both answers hurt: the first means spurious
  bounces on a cold Gradle daemon, the second means the gate quietly fails **open** exactly when the
  build is slowest. Until it's confirmed, `gates.json` is set generously rather than tuned
  (`lint-format` 300s, `arch-fitness` 600s — the first formatter auto-fix of a session and an `archTest`
  that has to compile test classes both run well past the old 180s/120s).

  **`e2e-audit-trail.sh --live` will not answer this** — it drives one *main-session* `developer` role
  with `--print`, so no subagent starts and `subagentStop` never fires; it verifies the audit-trail
  contract (`SESSION_START` / `SCOPE` / `SKILL_LOAD`), not gate behaviour.

  Answering it needs a deliberate probe: a throwaway `.github/hooks/*.json` wiring one `subagentStop`
  script with a small `timeoutSec`, driven three times in a session that fans out to a part. Three,
  not two — with only the timeout runs, "the part wasn't bounced" is unfalsifiable:

  | run | script | what it establishes |
  |---|---|---|
  | **control** | `exit 0` | what *accepted* looks like — the baseline the other two are read against |
  | **B** | `exit 1` immediately | **whether a non-zero `subagentStop` bounces a part at all.** The premise the whole fail-closed design rests on, and nothing in this PR has confirmed it. Run and interpret this one first — if it doesn't hold, the timeout question is moot |
  | **A** | `sleep` past `timeoutSec`, then `exit 1` | given B bounces: also bouncing ⇒ *timeout = failure*; accepted ⇒ *timeout = verdict dropped*, i.e. the gate fails **open** exactly when the build is slowest |

  Two traps that would each produce a confidently wrong answer:

  - **Do not let the probe fan out to `general-purpose`.** Per the known gap in this list, it emits no
    `subagentStart`/`Stop` at all — every run would look like "not bounced" and you would conclude the
    gates fail open when in truth they never fired. Spawn a **named** role (`developer`,
    `test-writer`).
  - **Confirm the hook fired, independently of what it decided.** `observability.json` already hooks
    `subagentStop`, so assert an `AGENT_STOP` record landed in `.apm-audit/sessions/<sessionId>.jsonl`
    for each run (`grep '"type":"AGENT_STOP"'`). Without it, "no bounce" and "no hook" are
    indistinguishable. Match on `"type"` — **not** on `"agent"`: the stack is popped before the record
    is emitted, so `AGENT_STOP` carries `"agent":"main"` (the parent) and names the stopping subagent
    in `"agentName"`. Filtering `AGENT_STOP` by `"agent":"developer"` yields nothing, while a bare
    `grep '"agent":"developer"'` matches the *`AGENT_START`* record and looks like a pass — both
    readings are wrong, in opposite directions.

  ### The answer (measured 2026-08-06, Copilot CLI 1.0.78)

  The probe was run as specified \u2014 a throwaway `.github/hooks/*.json` wiring one hook with
  `timeoutSec: 5`, driven against a **named** `developer` subagent (not `general-purpose`), with
  `AGENT_START`/`AGENT_STOP` asserted in `.apm-audit/` each time so "no bounce" could be told apart
  from "no hook". The CLI's own `events.jsonl` records each hook's verdict as `hook.end`, which makes
  the result independent of how the run looked.

  | event | hook did | CLI recorded | effect on the work |
  |---|---|---|---|
  | `subagentStop` | `exit 0` | `success: true` | part accepted |
  | `subagentStop` | `exit 1` | `success: false`, `Hook command failed with code 1` | **part accepted** |
  | `subagentStop` | slept past `timeoutSec` | `success: false`, `HookTimeoutError` | **part accepted** |
  | `preToolUse` | printed `allow` | `success: true` | tool ran |
  | `preToolUse` | `exit 1`, no decision | *hook errored* | **tool DENIED** |
  | `preToolUse` | slept past `timeoutSec` | timeout | **tool RAN** |

  Two conclusions, and both contradict what this file used to assume:

  **1. `subagentStop` cannot bounce anything.** A non-zero exit is *recorded and discarded*: the
  subagent's result is returned, the delegating session carries on, and the run completes normally.
  So `arch-fitness` and `verify-claims` are **advisory** on this CLI version \u2014 they still run, still
  log, and still tell a human exactly what is wrong, but nothing in the harness stops a bad part on
  their say-so. Their real teeth are in CI on the PR. Do not describe them as blocking, and do not
  design a control whose only enforcement point is `subagentStop`.

  **2. `preToolUse` fails in *both* directions, depending on how it fails.** Exiting non-zero without
  printing a decision is a **deny**; exceeding `timeoutSec` is an **allow**. That is the worst pair:
  the guard blocks the human when it crashes, and waves the agent through exactly when the machine is
  slow enough to matter. It also settles what the operator hit \u2014 the audit trail's
  `Denied by preToolUse hook from "..." (hook errored)` is reproduced *exactly* by a hook exiting
  non-zero, and not at all by a slow one. It was never a timeout.

  What changed as a result:

  - `guard-generated.sh` now carries an `EXIT` trap that emits a decision no matter how the script
    leaves, and always exits 0. `set -euo pipefail` means any unanticipated non-zero \u2014 a jq that dies
    on an unfamiliar payload, a future edit that adds a command \u2014 previously killed it before it
    printed anything, producing that opaque lockout. It still fails **closed**, but with a reason
    that names the script and says what to do. A control whose failure mode is "the human cannot work
    and cannot tell why" gets switched off within the hour, which leaves the tree genuinely unguarded.
  - The hook was cut from ~1.1s to ~0.75s per tool call by batching its jq calls into one spawn (each
    process spawn is ~300ms on Windows), and `governance.json`'s `timeoutSec` went 10 \u2192 60. Not
    because a timeout caused the lockout \u2014 it did not \u2014 but because a `preToolUse` timeout fails
    **open**, so every second of headroom is a second the guard is not silently skipped.
  - `gates.json` timeouts are left generous. Now that a `subagentStop` timeout is known to be
    harmless (logged, ignored), there is nothing to tune for.

## Using it

```sh
scripts/run-role.sh developer --ticket PROJ-123        # interactive session, audit armed
scripts/audit-report.sh --ticket PROJ-123              # the join, as markdown
scripts/audit-report.sh --ticket PROJ-123 --write docs/onboarding/PROJ-123-x/skill-usage.md
```

In a per-role worktree the hooks travel with the checkout (they're committed), and the trail is
per worktree — pass `--repo ../PROJ-123-po-dev-domain-cap` to the report to read it from the outside.

## Distribution to consuming repos

Hooks are **not an apm primitive** (apm deploys agents/instructions/skills only), so `apm install`
does not carry them. The blueprint repo's `scripts/pack-bundle.sh` ships this folder as
`build/hooks/` alongside the bundle; a consumer commits it at their repo root so part sessions in
backend/frontend/contract repos leave the same trail. See `apm-install.md` (blueprint repo).

Exactly two files in here are **consumer-owned** — `hooks.env` and `guard-generated.globs`. Both ship
fully inert, so the only install step is uncommenting the lines for that repo's stack and committing
them. Neither is gitignored on purpose: a gate reading an uncommitted `hooks.env` would behave
differently per workstation. Everything else — the `*.json` configs, `scripts/*.sh`, this README — is
framework-owned and is replaced wholesale on upgrade. **Framework rules must never live in the two
consumer-owned files**, since an upgrade cannot overwrite them; that is why `.github/hooks/*` is a
built-in deny in `guard-generated.sh` rather than a shipped glob.

That makes the copy command load-bearing, in both directions:

```sh
# first install — note the trailing `/.`: plain `cp -r src dst` NESTS when dst exists,
# landing the second drop at .github/hooks/hooks/ (pack-bundle.sh:149 hits the same trap).
mkdir -p .github/hooks && cp -r vendor/build/hooks/. .github/hooks/

# upgrade — framework files only. A blanket re-copy would silently revert the consumer's
# uncommented config back to the shipped inert version, and because both gates no-op when
# unset the regression is QUIET: no error, just gates that stopped gating.
cp -r vendor/build/hooks/scripts/. .github/hooks/scripts/
cp    vendor/build/hooks/*.json vendor/build/hooks/README.md .github/hooks/
cp -n vendor/build/hooks/hooks.env vendor/build/hooks/guard-generated.globs .github/hooks/
```

The `cp -n` line is a no-op once the consumer owns those two files, and seeds them on a repo that
somehow never got them. Anything else added to this folder later is framework-owned and belongs in
the unconditional lines above.

## Extending

> **This is a human operation by default.** `guard-generated.sh` denies an agent `Write`/`Edit`
> anywhere under `.github/hooks/` — including in *this* repo, where hooks are authored, and inside a
> `worktree-part.sh` part worktree (which keeps `.github/hooks/`, so a `skill-author` or `developer`
> part touching a hook hits the guard). That is intentional: these files execute at a lifecycle
> boundary with no approval prompt. When hook authoring **is** the session's job, launch it with
> `COPILOT_GUARD_ALLOW_HOOK_EDITS=1` — `run-role.sh` ends in `exec copilot`, so the launching shell's
> environment reaches the hook:
>
> ```sh
> COPILOT_GUARD_ALLOW_HOOK_EDITS=1 scripts/run-role.sh skill-author --ticket PROJ-123
> ```
>
> An agent's own `bash` child cannot set this — it would have to change the already-running CLI
> process's environment. Do not set it in a session that is doing something else; if it ends up in a
> shell profile it disables the guard for every later session, so when it fires the guard **allows
> with a reason** (`hook-edit guard BYPASSED for '<path>' …`) rather than silently — that string in a
> transcript where nobody was authoring hooks is the signal to go unset it.

Add an event array to `observability.json` (or a new `*.json`) and a `scripts/<name>.sh` (bash,
deterministic, fast; **observability scripts always exit 0**). CI validates the JSON and
`bash -n`/shellchecks the scripts (the blueprint repo's `ci.yml`), smoke-tests the log→report join, and
runs `scripts/e2e-audit-trail.sh` (blueprint-side) — a full e2e in a real `worktree-part.sh`-scoped worktree
(pruned SCOPE, used-vs-discovered split, per-agent attribution, leak row). Its `--live` flag
additionally drives one real `copilot` session locally to verify the **audit-trail** contract
(`SESSION_START` / `SCOPE` / `SKILL_LOAD`). Note what that does *not* cover: it runs a main-session
`developer` with `--print`, so no subagent starts and the `subagentStop` gates never fire — testing
those needs a session that actually fans out (see the timeout note above).
Per-developer hooks (not committed) go in `~/.copilot/hooks/*.json` with the same schema.

## Branch switches and pre-framework commits (absent hooks = allow, not deny)

Hook configs are read once at session start, but the scripts they invoke live in the working tree —
so a mid-session `git checkout` of a branch that predates the framework removes
`.github/hooks/scripts/` while the hooks stay registered. Every hook command therefore runs from the
repo root (`cwd: "."`) and checks its script exists before executing: **present** → runs with
`.github/hooks` as cwd, semantics unchanged (a crashing script still fails closed); **absent** →
`preToolUse` emits an explicit allow and gate/audit hooks exit 0. Without this, the first tool call
after such a checkout hit a spawn error and the fail-closed harness denied every subsequent call —
including the one that could have checked main back out (seen live on a consumer repo, 2026-08-06, during a
rebase onto a pre-v1.0.4 branch). Fail-open here is deliberately narrow: it applies only when the
script is missing from the checked-out commit, a state the guard's globs cannot protect anyway
(they gate agent Write/Edit, and the files do not exist on that commit to begin with).

`.gitattributes` (`* text eol=lf`) pins the whole tree to LF so `core.autocrlf=true` checkouts
cannot re-materialize the scripts with CRLF — git-bash tolerates CRLF scripts, but WSL bash and
strict shells do not.
