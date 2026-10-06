#!/usr/bin/env bash
# gate-common.sh — shared plumbing for the `SubagentStop` gates (Claude Code; advisory at exit 1).
#
# NOT a hook itself: sourced by scripts/lint-format.sh and scripts/arch-fitness.sh, which are the
# only two entries in gates.json. Three concerns live here because both gates need them identically
# and getting any of them subtly different between the two would be a silent hole:
#
#   gate_repo_root   locate the repo root, or FAIL CLOSED (a gate that can't find the tree must not
#                    report success — the CLI runs these with cwd `.claude/hooks`, so a bare `pwd`
#                    fallback would look like a root and quietly no-op).
#   gate_load_env    read `.claude/hooks/hooks.env` by PARSING, never by `.`-sourcing it.
#   gate_should_run  honour `agent_type` (Copilot: `agentName`) from the stdin payload so a gate only fires for the roles
#                    that actually write code.
#
# Callers set GATE_NAME before sourcing (used in every message).

# gate_repo_root — print the repo root; non-zero (with an ::error::) when there is no work tree.
gate_repo_root() {
  local root
  root="$(git rev-parse --show-toplevel 2>/dev/null || true)"
  if [ -z "$root" ]; then
    echo "::error::[${GATE_NAME}] not inside a git work tree (cwd '$PWD') — cannot locate the repo"
    echo "          root, so the gate cannot run. Refusing to report success."
    return 1
  fi
  printf '%s\n' "$root"
}

# gate_load_env <repo-root> — load the repo's gate config from .claude/hooks/hooks.env.
#
# hooks.env is PARSED, not sourced — but be precise about what that buys, because it is easy to
# over-read. The *_CMD values are `bash -c`'d by the gates; that is the entire point of the config.
# So a hooks.env containing `ARCH_FITNESS_CMD="touch PWNED"` still executes `touch PWNED` on the next
# subagentStop. What parsing removes is INCIDENTAL execution — a stray line, an `$(…)` sitting in a
# value, anything outside the six known keys — and it shrinks the payload shape from "arbitrary shell
# anywhere in the file" to "one command in one of the three *_CMD values" (the other three keys are
# an agent list, a git ref and a file path — never executed). It does NOT make a writable hooks.env
# safe. Whoever can write this file can run commands here; that is why `.claude/hooks/*` is an active
# glob in guard-generated.globs (which covers Write/Edit, not a `bash` tool call with a redirect —
# see that file). Treat hooks.env as code, not as inert data.
#
# Only `KEY=value` (optionally `export KEY=value`) lines for the six known keys are honoured; every
# other line — unknown key, or no `=` at all — is reported and ignored. Precedence is first-wins and
# announced: a value already exported in the environment beats the file, and an earlier line beats a
# later duplicate. Both are reported, because a silently-ignored value is the kind of thing that costs
# an afternoon (a stale exported ARCH_FITNESS_CMD looks exactly like a parser bug).
#
# Values may be single- or double-quoted; quoting is what lets a value carry a trailing `# comment`.
gate_load_env() {
  local file="$1/.claude/hooks/hooks.env" line key val
  [ -f "$file" ] || return 0
  while IFS= read -r line || [ -n "$line" ]; do
    line="${line#"${line%%[![:space:]]*}"}"           # ltrim
    line="${line%"${line##*[![:space:]]}"}"           # rtrim
    case "$line" in ''|'#'*) continue ;; esac
    case "$line" in 'export '*|$'export\t'*) line="${line#export}"; line="${line#"${line%%[![:space:]]*}"}" ;; esac
    # No `=` → reject BEFORE splitting. `${line%%=*}` on such a line yields the whole line as the key
    # AND `${line#*=}` yields it as the value, so a bare `ARCH_FITNESS_CMD` would run the literal
    # string `ARCH_FITNESS_CMD`, exit 127, and be reported as a layer-boundary violation — a diagnosis
    # pointing away from the actual cause (a typo in the config).
    case "$line" in
      *=*) ;;
      *) echo "[${GATE_NAME}] hooks.env: ignoring malformed line (no '='): '${line}'"; continue ;;
    esac
    key="${line%%=*}"
    case "$key" in
      LINT_FIX_CMD|LINT_CHECK_CMD|ARCH_FITNESS_CMD|GATE_AGENTS) ;;
      # verify-claims.sh: a ref and a file path, never a command — so unlike the three *_CMD keys
      # above, nothing here is ever `bash -c`'d. Kept in the same allow-list anyway, because the
      # alternative is a second config file with a second set of precedence rules.
      VERIFY_CLAIMS_BASE|VERIFY_CLAIMS_DECLARED) ;;
      *)
        echo "[${GATE_NAME}] hooks.env: ignoring unsupported entry '${key}' — only LINT_FIX_CMD,"
        echo "[${GATE_NAME}] LINT_CHECK_CMD, ARCH_FITNESS_CMD, GATE_AGENTS, VERIFY_CLAIMS_BASE and"
        echo "[${GATE_NAME}] VERIFY_CLAIMS_DECLARED are honoured (the file is parsed, not sourced,"
        echo "[${GATE_NAME}] so shell in it never runs)."
        continue ;;
    esac
    val="${line#*=}"
    case "$val" in
      \"*) val="${val#\"}"; val="${val%%\"*}" ;;      # "…"  — drops any trailing # comment
      \'*) val="${val#\'}"; val="${val%%\'*}" ;;      # '…'
    esac
    # First wins — from the environment, or from an earlier line in this file (line N exports the key,
    # so a duplicate lands here too). Say so: the shipped hooks.env defines the same three keys in both
    # the Backend and Frontend blocks, so uncommenting both silently drops the second set.
    if [ -n "${!key:-}" ]; then
      echo "[${GATE_NAME}] hooks.env: '${key}' is already set ($(gate_origin "$key")) — keeping that,"
      echo "[${GATE_NAME}] ignoring '${val}'."
      continue
    fi
    printf -v "$key" '%s' "$val"
    printf -v "GATE_SRC_${key}" '%s' 'hooks.env'
    export "${key?}"
  done < "$file"
}

# gate_origin <KEY> — where the effective value came from. Used both in the duplicate/precedence
# message above and on the "running: …" line, so a stale exported value is visible instead of silent.
# The `unset` branch is unreachable from today's three call sites (all guarded by a non-empty check
# on the value), but "not hooks.env" must not silently mean "environment" the day a fourth appears.
gate_origin() {
  local src="GATE_SRC_$1"
  if   [ -z "${!1:-}" ];              then printf '%s' 'unset'
  elif [ "${!src:-}" = "hooks.env" ]; then printf '%s' 'from .claude/hooks/hooks.env'
  else                                     printf '%s' 'from the environment — overrides hooks.env'
  fi
}

# gate_should_run <stdin-payload> — 0 when this subagentStop belongs to a code-writing role.
#
# `subagentStop` fires for EVERY subagent, so without this filter `analyst`, `reviewer`,
# `design-critic`, `retro`, `pattern-scanner` … each pay a full formatter + fitness run for code they
# never wrote, and can be bounced for state they never touched. The payload carries `agent_type`
# (Claude Code; `agentName` on Copilot), so use it.
#
# Direction of failure: we skip only when the role is POSITIVELY identified as non-code-writing.
# No `jq`, no `agent_type`, unparseable payload → the gate RUNS. Unknown identity must not be a way to
# slip past a fail-closed gate. Override the allow-list per repo with GATE_AGENTS in hooks.env.
gate_should_run() {
  local payload="${1:-}" agent="" allow
  if command -v jq >/dev/null 2>&1; then
    agent="$(printf '%s' "$payload" | jq -r '.agent_type // .agentName // .agent_name // .AgentName // ""' 2>/dev/null || true)"
  fi
  [ -n "$agent" ] || return 0                         # identity unknown → run the gate
  allow="${GATE_AGENTS:-developer test-writer contract-agent}"
  case " $allow " in
    *" $agent "*) return 0 ;;
  esac
  echo "[${GATE_NAME}] skipped — agent '$agent' does not write code (GATE_AGENTS='$allow')."
  return 1
}
