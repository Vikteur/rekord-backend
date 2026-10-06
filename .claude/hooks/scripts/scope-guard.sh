#!/usr/bin/env bash
# scope-guard.sh — fail-closed PreToolUse hook (Claude Code): enforce each agent's write and
# command fence.
#
# The Copilot agents declared `allowedFilePaths` and `commandAllowlist` in their frontmatter. Claude
# Code subagents have no such fields, so the fences live in `.claude/hooks/agent-scopes.json` (keyed
# by agent name) and this hook enforces them on every Write/Edit/NotebookEdit/Bash call:
#
#   Write/Edit   target path must fall inside the agent's `allowedFilePaths`
#                (`dir/` = prefix, otherwise exact path or bash glob where `*` spans `/`).
#                `allowedFilePaths` absent = any path; `[]` = no writes at all.
#   Bash         every command segment (split on ; && || | & and newlines, outside quotes) must
#                start with an entry of the agent's `commandAllowlist`. `cd` is always allowed.
#                Command substitution is denied except the `$(cat <<'EOF' … )` heredoc form used
#                for commit/PR messages.
#
# Who is fenced: the `agent_type` field Claude Code puts on every event fired inside a subagent (or a
# session started with `--agent`). No agent_type, or an agent with no entry → not this hook's
# business (exit 0, no output — normal permission flow applies).
#
# Contract: JSON payload on stdin, decision JSON on stdout, exit 0. "No objection" prints NOTHING:
# in Claude Code `permissionDecision:"allow"` would skip the user's permission prompt.
# Failure direction: missing policy / unparseable payload → no objection (fail open, like
# guard-generated.sh); an error AFTER the agent was identified → deny with a reason (EXIT trap).
#
# RESIDUAL, stated plainly: this reads the command string. It does not see what a script the agent is
# allowed to run does, nor a redirect (`git log > file`) inside an allowed command.
# Keep this file bash-3.2-clean (no mapfile, no ${x,,}, no declare -A) — see README.
set -uo pipefail

here="$(cd "$(dirname "$0")" && pwd)"
policy="${CLAUDE_SCOPE_POLICY:-$here/../agent-scopes.json}"

decided=0
armed=0
emit_fallback_deny() {
  [ "$decided" -eq 1 ] && return 0
  [ "$armed" -eq 1 ] || return 0                 # not yet identified as a fenced agent: no objection
  printf '%s\n' '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"BLOCKED: the agent scope guard (.claude/hooks/scripts/scope-guard.sh) failed before it could decide, so it is denying. This is a bug in the hook, not a judgement about your call."}}'
  decided=1
}
trap 'emit_fallback_deny; exit 0' EXIT

allow() { decided=1; exit 0; }
deny() { decided=1
  jq -cn --arg r "$1" \
    '{hookSpecificOutput:{hookEventName:"PreToolUse",permissionDecision:"deny",permissionDecisionReason:$r}}'
  exit 0
}

[ -f "$policy" ] || allow
payload="$(cat 2>/dev/null || true)"

# One jq spawn for everything (each spawn costs ~300ms on Windows). Fields joined by U+0001, list
# items by U+0002; trailing sentinel keeps "jq failed" distinguishable from "all empty".
if ! fields="$(printf '%s' "$payload" | jq -j --slurpfile pol "$policy" '
      (.agent_type // "") as $ag
      | (if $ag == "" then null else $pol[0].agents[$ag] end) as $s
      | (.tool_input // {}) as $a
      | $ag + "\u0001" + (.tool_name // "") + "\u0001"
        + ($a.file_path // $a.notebook_path // $a.path // "") + "\u0001"
        + ($a.command // "") + "\u0001"
        + (.cwd // "") + "\u0001"
        + (if $s == null then "none" elif ($s | has("allowedFilePaths")) then "fenced" else "any" end) + "\u0001"
        + (($s.allowedFilePaths // []) | join("\u0002")) + "\u0001"
        + (($s.commandAllowlist // []) | join("\u0002")) + "\u0001."' 2>/dev/null)"; then
  allow
fi

agent="${fields%%$'\001'*}";  fields="${fields#*$'\001'}"
tool="${fields%%$'\001'*}";   fields="${fields#*$'\001'}"
path="${fields%%$'\001'*}";   fields="${fields#*$'\001'}"
cmd="${fields%%$'\001'*}";    fields="${fields#*$'\001'}"
cwd="${fields%%$'\001'*}";    fields="${fields#*$'\001'}"
mode="${fields%%$'\001'*}";   fields="${fields#*$'\001'}"
paths="${fields%%$'\001'*}";  fields="${fields#*$'\001'}"
cmds="${fields%%$'\001'*}"

[ "$mode" = "none" ] && allow
armed=1
policy_rel=".claude/hooks/agent-scopes.json"

# ── Write / Edit ─────────────────────────────────────────────────────────────────────────────────
check_path() {
  [ "$mode" = "any" ] && allow
  [ -n "$path" ] || allow

  local p="${path//\\//}" root entry IFS
  while [ "$p" != "${p//\/\//\/}" ]; do p="${p//\/\//\/}"; done
  # Claude Code passes absolute paths: make them relative to the session cwd (a worktree, if the
  # agent runs in one), else to the project dir. Case-insensitive: Windows casing varies.
  shopt -s nocasematch
  for root in "$cwd" "${CLAUDE_PROJECT_DIR:-}"; do
    root="${root//\\//}"; root="${root%/}"
    [ -n "$root" ] || continue
    case "$p" in "$root"/*) p="${p:${#root}+1}"; break ;; esac
  done
  shopt -u nocasematch
  while [ "$p" != "${p//\/.\//\/}" ]; do p="${p//\/.\//\/}"; done
  p="${p#./}"

  case "$p" in
    /*|[A-Za-z]:/*) deny "BLOCKED: agent '$agent' may only write inside its fence ($policy_rel), and '$path' is outside the project/worktree." ;;
    ../*|*/../*|..) deny "BLOCKED: agent '$agent' may not write via '..' paths ('$path')." ;;
  esac

  IFS=$'\002'
  for entry in $paths; do
    [ -n "$entry" ] || continue
    case "$entry" in
      */) case "$p" in "$entry"*) allow ;; esac ;;
      *)  # shellcheck disable=SC2053  # intentional glob match
          if [[ "$p" == $entry ]]; then allow; fi ;;
    esac
  done
  unset IFS
  if [ -z "$paths" ]; then
    deny "BLOCKED: agent '$agent' is read-only (empty allowedFilePaths in $policy_rel) and may not write '$p'."
  fi
  deny "BLOCKED: agent '$agent' may only write under: $(printf '%s' "$paths" | tr '\002' ' '). '$p' is outside that fence ($policy_rel). Report it back to the orchestrator instead of widening your scope."
}

# ── Bash ─────────────────────────────────────────────────────────────────────────────────────────
norm_cmd() {  # strip a leading interpreter and ./ so `bash ./scripts/x.sh` matches `scripts/x.sh`
  local s="$1"
  case "$s" in "bash "*|"sh "*) s="${s#* }"; s="${s#"${s%%[![:space:]]*}"}" ;; esac
  s="${s#./}"
  printf '%s' "$s"
}

seg_allowed() {  # seg_allowed <segment> — 0 when the segment starts with an allowlisted command
  local s entry e IFS
  s="$(norm_cmd "$1")"
  [ -n "$s" ] || return 0
  case "$s" in cd|"cd "*) return 0 ;; esac
  IFS=$'\002'
  for entry in $cmds; do
    e="$(norm_cmd "$entry")"
    [ -n "$e" ] || continue
    if [ "$s" = "$e" ]; then return 0; fi
    case "$s" in "$e "*|"$e"$'\t'*) return 0 ;; esac
  done
  return 1
}

check_cmd() {
  [ -n "$cmd" ] || allow
  [ -n "$cmds" ] || deny "BLOCKED: agent '$agent' has no commandAllowlist in $policy_rel, so it may not run shell commands."

  # Command substitution hides a second command inside an allowed one. Permit only the
  # `$(cat <<…` heredoc used for commit and PR bodies.
  local rest="$cmd"
  rest="${rest//\$(cat <</}"
  case "$rest" in
    *'$('*|*'`'*) deny "BLOCKED: agent '$agent' may not use command substitution (\$( ) or backticks) — it can hide a command outside the allowlist. Only \$(cat <<'EOF' … EOF) message heredocs are allowed." ;;
  esac

  # Split on ; & | and newlines OUTSIDE quotes; each segment is checked on its own.
  local i c q="" seg="" n=${#cmd}
  i=0
  while [ "$i" -lt "$n" ]; do
    c="${cmd:$i:1}"
    if [ -n "$q" ]; then
      [ "$c" = "$q" ] && q=""
      [ "$c" = "\\" ] && [ "$q" = '"' ] && { seg="$seg$c"; i=$((i + 1)); c="${cmd:$i:1}"; }
      seg="$seg$c"
    else
      case "$c" in
        "'"|'"') q="$c"; seg="$seg$c" ;;
        ';'|'&'|'|'|$'\n')
          seg="${seg#"${seg%%[![:space:]]*}"}"
          seg_allowed "$seg" || deny "BLOCKED: agent '$agent' may not run '${seg%% *}…' — allowed commands: $(printf '%s' "$cmds" | tr '\002' ',' | sed 's/,/, /g') ($policy_rel)."
          seg="" ;;
        *) seg="$seg$c" ;;
      esac
    fi
    i=$((i + 1))
  done
  seg="${seg#"${seg%%[![:space:]]*}"}"
  seg_allowed "$seg" || deny "BLOCKED: agent '$agent' may not run '${seg%% *}…' — allowed commands: $(printf '%s' "$cmds" | tr '\002' ',' | sed 's/,/, /g') ($policy_rel)."
  allow
}

case "$tool" in
  Write|Edit|MultiEdit|NotebookEdit) check_path ;;
  Bash) check_cmd ;;
  *) allow ;;
esac
allow
