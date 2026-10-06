#!/usr/bin/env bash
# lint-format.sh — Claude Code `SubagentStop` gate (advisory): the blueprint's **lint-format** check, local half.
#
# templates/hooks-and-gates.md stages `lint-format` (eslint+prettier / your backend formatter) as a
# formatting gate.
# THIS hook runs it the instant a code-writing subagent finishes a part: it auto-formats the
# just-written code and verifies it — so the agent never ships formatting-red work. Deterministic and
# boot-friendly: the formatter jar is cached, so it runs offline on the workstation.
#
# Unlike the observability hooks (always exit 0), this is a GATE: a non-zero exit bounces the part back.
# Auto-fix, then verify. `LINT_FIX_CMD` normalizes the tree IN PLACE. `LINT_CHECK_CMD` then confirms
# nothing remains unformatted; if something does (a rule with no auto-fixer) the hook fails. When a
# repo enforces formatting ONLY here (the check dropped from CI), set `LINT_CHECK_CMD` too so this is a
# real gate, not just a silent auto-format.
#
# On the auto-fix edits: `subagentStop` fires when the subagent FINISHES, so if it already committed
# its part, the reformat lands as uncommitted working-tree changes — NOT inside that commit. Nothing
# in the contract makes them ride along. So the hook prints the paths it dirtied on stdout (which the
# contract surfaces to the model) and the agent is expected to fold them in; otherwise the next role
# inherits them as unexplained dirt, or a later `git add -A` sweeps them into an unrelated commit.
#
# The concrete commands are per-repo config in hooks.env (this blueprint is generic):
#
#   LINT_FIX_CMD     e.g. ./gradlew <formatter>Apply   (backend)  /  npm run format   (frontend)
#   LINT_CHECK_CMD   e.g. ./gradlew <formatter>Check   (backend)  /  npm run lint     (frontend)
#
# With neither set it is an informative no-op, so the scaffold ships safely before a repo supplies a
# formatter. NOTE: a formatter's `ratchetFrom("origin/main")`-style option only touches files changed
# vs the base, so the `origin/main` ref must exist locally (it does after any clone/fetch).
#
# Contract (Claude Code hooks — SubagentStop):
#   stdin  : JSON ({session_id, agent_type, cwd, …}); `agent_type` selects whether this gate applies.
#   stdout : free-text surfaced to the model as context.
#   exit 0 : gate passed (or not applicable);  exit 1 : gate failed — ADVISORY in Claude Code
#            (reported, not blocking). Exit 2 would block the subagent; see README "Gate hooks".
#
#   ON "the part bounces back": it did not on Copilot CLI 1.0.78, and exit 1 does not in Claude Code either. A probe (README.md,
#   "The answer") shows a non-zero subagentStop exit is recorded as `success: false` and then
#   ignored — the part is accepted either way. This gate is therefore ADVISORY: its value is the
#   message it puts in front of a human seconds after the mistake, not an enforcement it cannot
#   deliver. Keep returning non-zero (it is the honest signal, it lands in the transcript, and it
#   becomes enforcement the day the CLI honours it) — but do not rely on it to stop anything.

set -uo pipefail
payload="$(cat 2>/dev/null || true)"

export GATE_NAME=lint-format
# shellcheck source=/dev/null
. "$(cd "$(dirname "$0")" && pwd)/gate-common.sh"

# Fail CLOSED on anything that stops the gate from doing its job. `|| exit 0` here would mean a gate
# whose whole contract is "non-zero bounces the part" reports success on error.
root="$(gate_repo_root)" || exit 1
cd "$root" || { echo "::error::[lint-format] cannot cd to repo root '$root'"; exit 1; }

# Order is deliberate: GATE_AGENTS comes OUT of hooks.env, so the config must load before the agent
# filter can honour a repo's override. The cost is that a skipping role still parses the file (and may
# print a warning about it) before deciding it has nothing to do — cheap, and worth it. Do not swap.
gate_load_env "$root"                 # parses .claude/hooks/hooks.env; never sources it
gate_should_run "$payload" || exit 0  # not a code-writing role → nothing to format

fix="${LINT_FIX_CMD:-}"
check="${LINT_CHECK_CMD:-}"

if [ -z "$fix" ] && [ -z "$check" ]; then
  echo "[lint-format] not configured (LINT_FIX_CMD / LINT_CHECK_CMD unset) — skipping the local"
  echo "[lint-format] auto-format + verify. Set them in .claude/hooks/hooks.env to enforce it, e.g."
  echo "[lint-format]   LINT_FIX_CMD=\"./gradlew <formatter>Apply\""
  echo "[lint-format]   LINT_CHECK_CMD=\"./gradlew <formatter>Check\""
  echo "[lint-format] See README.md and templates/hooks-and-gates.md."
  exit 0
fi

# 1. Auto-fix: normalize the just-written code in place. A non-zero here means the formatter itself
#    failed to RUN (bad config / missing tool / cold cache under --offline) — not merely "found
#    unformatted code" — so surface it. Capture the status directly (rc=$?): `if ! cmd` would set $?
#    to the negated status, masking it.
if [ -n "$fix" ]; then
  echo "[lint-format] auto-formatting: $fix   (LINT_FIX_CMD $(gate_origin LINT_FIX_CMD))"
  bash -c "$fix"; rc=$?
  if [ "$rc" -ne 0 ]; then
    echo "::error::[lint-format] formatter failed to run (exit $rc): $fix"
    exit "$rc"
  fi
  dirty="$(git status --porcelain 2>/dev/null || true)"
  if [ -n "$dirty" ]; then
    echo "[lint-format] the working tree is dirty after formatting — fold these into the part's"
    echo "[lint-format] commit before handing it on (they are NOT in it yet):"
    printf '%s\n' "$dirty" | sed 's/^/[lint-format]   /'
  fi
fi

# 2. Verify: confirm nothing remains unformatted (e.g. a rule with no auto-fixer). A failure here means
#    the code could not be auto-normalized — the part goes back to its developer.
if [ -n "$check" ]; then
  echo "[lint-format] verifying: $check   (LINT_CHECK_CMD $(gate_origin LINT_CHECK_CMD))"
  bash -c "$check"; rc=$?
  if [ "$rc" -ne 0 ]; then
    echo "::error::[lint-format] code is not formatted and could not be auto-fixed (exit $rc). The part"
    if [ -n "$fix" ]; then
      echo "          goes back to its developer — run '$fix' locally and inspect the remaining diff."
    else
      echo "          goes back to its developer — no LINT_FIX_CMD is set, so fix the reported files by"
      echo "          hand (or set LINT_FIX_CMD in .claude/hooks/hooks.env to auto-fix first)."
    fi
    exit "$rc"
  fi
fi

echo "[lint-format] PASSED — code is formatted."
exit 0
