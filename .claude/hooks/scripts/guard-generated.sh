#!/usr/bin/env bash
# guard-generated.sh — fail-closed PreToolUse hook (Claude Code): DENY hand-edits to generated code, and to the
# hook config itself.
#
# TWO rules, deliberately in different places because they have opposite update policies:
#
#   1. BUILT-IN (here, framework-owned): `.claude/hooks/*` and `.claude/settings*.json` — see the block below.
#   2. CONFIGURED (consumer-owned): the generated-path globs in `.claude/hooks/guard-generated.globs`
#      — one glob per line; `*` spans `/`, bash `[[ ]]` semantics; `#` = comment. Enforces
#      constitution P4 (contract-first): generated API clients / server stubs / DTOs are regenerated
#      from the OpenAPI spec, never hand-edited.
#
# A Write/Edit whose target path matches either is DENIED; everything else is allowed.
#
# Claude Code hook contract: JSON payload on stdin (tool_name, tool_input.file_path|command), a JSON permission decision on stdout, exit 0.
# The DENY is signalled by the `permissionDecision` field, not the exit code. This hook FAILS OPEN
# on any parse error / missing jq / missing config (emits allow) so it can never break or stall a
# session — governance that can't parse must not deny blindly.
set -euo pipefail

here="$(cd "$(dirname "$0")" && pwd)"
globs_file="${CLAUDE_GUARD_GLOBS_FILE:-${COPILOT_GUARD_GLOBS_FILE:-$here/../guard-generated.globs}}"
# CLAUDE_* is the name; the COPILOT_* spelling is still honoured so an old launcher keeps working.
allow_hook_edits="${CLAUDE_GUARD_ALLOW_HOOK_EDITS:-${COPILOT_GUARD_ALLOW_HOOK_EDITS:-}}"

# ── Never exit without a decision ────────────────────────────────────────────────────────────────
# MEASURED (Copilot CLI 1.0.78, three-run probe recorded in README.md): on preToolUse, a hook that
# exits non-zero WITHOUT printing a decision is treated as DENY and the operator sees
# `Denied by preToolUse hook from "..." (hook errored)` with nothing to act on. That is the lockout
# in the audit trail, and it is not a timeout - a hook that exceeds timeoutSec is ALLOWED, the
# opposite direction.
#
# This script runs `set -euo pipefail`, so ANY unanticipated non-zero - a jq that dies on a payload
# shape we did not predict, a read error on the globs file, a future edit that adds a command - kills
# it before any decision reaches stdout, and the whole session stops with an opaque message. A
# security control whose failure mode is "the human cannot work, and cannot tell why" gets disabled
# within the hour, which leaves the tree unguarded for real.
#
# So: emit a decision no matter how we leave. Fail CLOSED (deny) to keep the control's intent, but
# say what happened and how to proceed - an actionable denial instead of an inscrutable one. The
# JSON is hand-built with no interpolation because this path must survive a broken jq, which is
# exactly one of the ways we get here.
decided=0
emit_fallback_deny() {
  [ "$decided" -eq 1 ] && return 0
  printf '%s\n' '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"BLOCKED: the generated-code guard (.claude/hooks/scripts/guard-generated.sh) failed before it could decide, so it is denying rather than waving the call through. This is a bug in the hook, not a judgement about your edit. Re-run the tool call; if it persists, run the hook by hand to see the error: printf %s \"<payload>\" | bash .claude/hooks/scripts/guard-generated.sh PreToolUse"}}'
  decided=1
}
# exit 0 always: the decision travels in stdout, and a non-zero exit is what produces the opaque
# message this trap exists to replace.
trap 'emit_fallback_deny; exit 0' EXIT

# CLAUDE CODE: "allow" is NOT neutral here — permissionDecision:"allow" skips the user's permission
# prompt. So "no objection" is exit 0 with NO output, which defers to the normal permission flow.
allow() { decided=1; exit 0; }
allow_reason() { decided=1; # <reason> — no objection, but say WHY (shown to the user), so a bypass is visible
  jq -cn --arg r "$1" '{systemMessage:$r}'
  exit 0
}
deny() { decided=1; # <reason>
  jq -cn --arg r "$1" \
    '{hookSpecificOutput:{hookEventName:"PreToolUse",permissionDecision:"deny",permissionDecisionReason:$r}}'
  exit 0
}

payload="$(cat 2>/dev/null || true)"
# ONE jq invocation for every field this hook needs, not one per field.
#
# This is a preToolUse hook: it runs before EVERY tool call, and on Windows each process spawn costs
# ~300ms (measured on the affected workstation: bash startup 320ms, jq startup ~330ms, `command -v
# jq` 145ms). The original shape - `command -v jq`, then a jq per field - put this hook at ~1.1s per
# tool call against a 10s `timeoutSec`: under 10x headroom on a machine where antivirus can stall a
# process spawn for seconds. A hook that DENIES on error has no safe way to be slow, because
# exceeding the budget reads as "hook errored" and blocks the operator - which is what happened in
# practice. Batching to a single spawn roughly halves the cost; the timeout was raised as well,
# because both were wrong.
#
# The `command -v jq` probe is gone rather than moved: a missing jq makes the call below fail, which
# lands in the same fail-open branch. Same behaviour, one less spawn.
#
# Fields are joined with U+0001, which cannot appear in a path or a command. NOT NUL: a bash variable
# cannot hold a NUL byte, so that idiom would silently truncate at the first field. The trailing
# sentinel keeps the output non-empty when all three fields are empty, so "jq failed" stays
# distinguishable from "nothing to extract".
if ! fields="$(printf '%s' "$payload" | jq -j '
      (.toolArgs // .tool_args // .toolInput // .tool_input // {}) as $a
      | ((.toolName // .tool_name // "") + "\u0001"
         + ($a.file_path // $a.notebook_path // $a.path // $a.filePath // $a.target_file // "") + "\u0001"
         + ($a.command // $a.cmd // $a.script // "") + "\u0001.")' 2>/dev/null)"; then
  allow                                         # no jq, or unparseable payload: fail open
fi
[ -n "$fields" ] || allow

# Split on the sentinel with parameter expansion, not `read`: a shell command legitimately contains
# newlines, and `read` would stop at the first one.
tool="${fields%%$'\001'*}";  fields="${fields#*$'\001'}"
path="${fields%%$'\001'*}";  fields="${fields#*$'\001'}"
cmd="${fields%%$'\001'*}"

# ── Rule 1b: the audit trail is not the agent's to destroy ─────────────────────────────────
# An audit trail is only evidence if it sits on a surface the acting party cannot rewrite. Rules 1
# and 2 gate Write/Edit, which does nothing here: `.apm-audit/` is destroyed with `rm -rf`, not with
# an editor. So this rule reads the SHELL tool instead — the one place an agent can reach the trail.
#
# Deliberately narrow, because a guard that fires on innocent commands gets switched off:
#   • the command must NAME .apm-audit *and* carry a destructive verb (rm/rmdir/mv/truncate/shred/
#     find -delete), or
#   • it must be `git clean` with -x/-X, which deletes ignored files and therefore takes the trail
#     out without ever naming it — the case that would otherwise look completely innocent.
# Reading, grepping, tailing, `mkdir -p` and appending are all still allowed; those are the trail
# working as intended.
#
# RESIDUAL, stated plainly: this sees the command string of a tool call. It does not stop a script
# the agent wrote and then executed, a redirect built by string concatenation, or anything that
# reaches the directory without spelling its name. The durable fix is shipping the trail off the
# workstation (see the hooks README); this closes the careless path, not the determined one.
case "$tool" in
  Bash|bash|shell|Shell|run_in_terminal|runCommands|execute_command|executeCommand)
    if [ -n "$cmd" ]; then
      norm_cmd="${cmd//\\//}"          # backslashes -> / so a Windows-style path still reads as .apm-audit
      case "$norm_cmd" in
        *.apm-audit*)
          case "$norm_cmd" in
            *rm\ *|*rm-*|*rmdir*|*" mv "*|*truncate*|*shred*|*-delete*|*unlink*)
              deny "BLOCKED: this command removes or rewrites '.apm-audit/', the harness audit trail. An audit trail an agent can delete is not an audit trail — it records what you did, so it is not yours to edit. If it genuinely needs clearing, a human should do it outside an agent session. Reading, grepping and appending to it are unaffected."
              ;;
          esac
          ;;
      esac
      case "$norm_cmd" in
        *"git clean"*)
          case "$norm_cmd" in
            *-*x*|*-*X*)
              deny "BLOCKED: 'git clean' with -x/-X deletes IGNORED files, which includes '.apm-audit/' — the harness audit trail — without naming it. Drop -x/-X, or scope the clean to a path (git clean -fd <dir>). If wiping ignored files is genuinely the task, a human should run it outside an agent session."
              ;;
          esac
          ;;
      esac
    fi
    allow                                       # shell command, nothing destructive matched
    ;;
esac

case "$tool" in
  Write|Edit|MultiEdit|NotebookEdit|create_file|edit_file|editFiles|replace_string_in_file|multi_replace_string_in_file|str_replace_editor|apply_patch) ;;
  *) allow ;;                                   # not a write/edit tool
esac

# Target path across arg-shape variants (CLI `toolArgs`, VS Code `toolInput`) - already extracted
# above in the single jq pass.
[ -n "$path" ] || allow

# Normalise the spellings that reach the same file on disk. Rule 1 is a security control against an
# agent, so it should not be defeatable by typing the path oddly; rule 2 inherits the same treatment
# because a consumer's globs describe real repo paths either way.
path="${path//\\//}"                                                        # backslashes → /
while [ "$path" != "${path//\/\//\/}" ]; do path="${path//\/\//\/}"; done   # collapse //  → /
while [ "$path" != "${path//\/.\//\/}" ]; do path="${path//\/.\//\/}"; done # collapse /./ → /
path="${path#./}"                                                           # drop a leading ./
# Claude Code passes ABSOLUTE paths: make them repo-relative so `.claude/hooks/*` and the consumer's
# relative globs match. Case-insensitive prefix strip (Windows drive/user casing varies).
proj="${CLAUDE_PROJECT_DIR:-}"; proj="${proj//\\//}"; proj="${proj%/}"
if [ -n "$proj" ]; then
  shopt -s nocasematch
  case "$path" in "$proj"/*) path="${path:${#proj}+1}" ;; esac
  shopt -u nocasematch
fi

# ── Rule 1: built-in self-protection ─────────────────────────────────────────────────────────────
# `hooks.env` holds the *_CMD values the subagentStop gates `bash -c`, and `scripts/*.sh` ARE those
# gates, so an agent that can rewrite either gets command execution at a lifecycle boundary with no
# tool-approval prompt in between. Hard-coded rather than a line in guard-generated.globs, because
# that file is CONSUMER-owned and this rule is framework-owned — three consequences of getting that
# wrong, all of which the glob version had:
#   • an upgrade must not clobber a consumer's globs file, so a framework rule shipped in it would
#     never reach any repo that already had one — i.e. every existing consumer;
#   • the opt-in default is "no globs file at all", and the check below fails open on that, so those
#     consumers would get no self-protection either;
#   • a rule protecting `.claude/hooks/*` from inside `.claude/hooks/` is circular.
# This runs BEFORE the globs-file existence check for exactly that second reason.
#
# Human-editable, agent-deny: humans change hooks directly. When hook authoring IS the session's job
# (this framework repo), the human launches it with CLAUDE_GUARD_ALLOW_HOOK_EDITS=1 — an env var on
# the CLI process, which an agent's own `bash` child cannot change. Residual, as ever: this sees
# Write/Edit tool calls, not a `bash` redirect.
# Matched case-INSENSITIVELY: `.Claude/hooks/hooks.env` is the same file on Windows (where this team
# works) and on macOS, so a case variant must not read as an unrelated path.
#
# Via `nocasematch` (bash 3.1+), NOT a lowercase-copy parameter expansion: that form is bash 4 only,
# and macOS still ships bash 3.2 as /bin/bash, where it is a `bad substitution` that kills the script
# BEFORE any allow/deny is printed. No output means no parseable decision, which per the contract
# above means fail open — so a bash-4-ism here would silently disable the ENTIRE guard, rule 2
# included, on a subset of workstations. Keep this file bash-3.2-clean; CI gates it.
shopt -s nocasematch
case "$path" in
  .claude/hooks/*|*/.claude/hooks/*|.claude/settings.json|*/.claude/settings.json|.claude/settings.local.json|*/.claude/settings.local.json)
    # Explicit if, not `a && b || c`: allow_reason/deny both exit, so the terse form works today, but
    # the next edit to this block is where that shape usually goes wrong.
    if [ "$allow_hook_edits" = 1 ]; then
      # Say so. A hatch set once for a legitimate hook-authoring session and left in a shell profile
      # would otherwise disable this guard in every session afterwards with nothing in the transcript
      # — the same silent-override shape the gates' `gate_origin` exists to prevent.
      allow_reason "hook-edit guard BYPASSED for '$path' — CLAUDE_GUARD_ALLOW_HOOK_EDITS=1 is set in this session's environment. Intended only for sessions whose job is authoring hooks; if that is not this session, unset it (check your shell profile)."
    else
      deny "BLOCKED: '$path' is Claude Code hook config/code (hook scripts or the settings that wire them). It executes automatically at a lifecycle boundary with no tool-approval prompt, so it is not agent-editable. This is NOT generated code — there is no contract to regenerate it from. Ask a human to make the change, or relaunch the session with CLAUDE_GUARD_ALLOW_HOOK_EDITS=1 if authoring hooks is the task."
    fi
    ;;
esac
# Load-bearing, and unconditional on purpose: rule 2's `[[ "$path" == $glob ]]` must be
# case-SENSITIVE whatever the environment says (BASHOPTS can carry nocasematch into a child bash),
# because consumer globs describe real repo paths and this hook must not change their meaning.
shopt -u nocasematch

# ── Rule 2: consumer-configured generated paths ──────────────────────────────────────────────────
[ -f "$globs_file" ] || allow                    # no config → nothing guarded (opt-in)

while IFS= read -r line || [ -n "$line" ]; do
  glob="${line%%#*}"; glob="$(printf '%s' "$glob" | tr -d '[:space:]')"
  [ -n "$glob" ] || continue
  # shellcheck disable=SC2053  # intentional glob match; unquoted RHS so `*` spans '/'
  if [[ "$path" == $glob ]]; then
    deny "BLOCKED: '$path' is generated code (matches '$glob'). Regenerate it from the OpenAPI contract; never hand-edit. See constitution P4 (contract-first)."
  fi
done < "$globs_file"

allow
