#!/usr/bin/env bash
# audit-log.sh — append one Claude Code lifecycle event to the per-session audit trail (JSONL).
#
# This is the "harness load log" leg of the audit trail (see .claude/hooks/README.md): every
# session/tool/subagent event lands in .apm-audit/sessions/<sessionId>.jsonl. Three tiers of
# skill/instruction/doc observation feed the per-agent report (scripts/audit-report.sh) — docs
# (DOC_SEEN/DOC_LOAD, any docs/**.md; SCOPE lists the docs/code-maps tree) answer whether the
# code-maps a skill points at are actually read:
#
#   SCOPE              (sessionStart)  what was AVAILABLE — the deployed .claude/skills/ dirs +
#                                      .claude/rules/ files present in this checkout
#   *_SEEN             (postToolUse)   what was DISCOVERED — a skill/instruction path that only
#                                      appeared in a tool RESULT (ls / grep / file-search output
#                                      scrolled past the agent) without being opened by that call
#   *_LOAD             (postToolUse)   what was READ & USED — the path appears in the tool ARGS
#                                      (an explicit view/cat of the body), stamped with the
#                                      file's last-touch commit + dirty flag at that moment
#
# Usage (wired via observability.json; the CLI runs it with cwd=.claude/hooks):
#   ./scripts/audit-log.sh <event>       # event: sessionStart|userPrompt|postToolUse|
#                                        #        postToolUseFailure|subagentStart|subagentStop|
#                                        #        sessionEnd
#
# Contract (Claude Code hooks; <event> keeps the original camelCase names — see settings.json):
#   stdin  : JSON payload — session_id, cwd, hook_event_name, plus per event: tool_name/tool_input/
#            tool_response (PostToolUse*), agent_type (inside a subagent, and on SubagentStart/Stop),
#            prompt (UserPromptSubmit), reason (SessionEnd). Copilot camelCase still tolerated.
#   stdout : nothing the model needs — observability only.
#   exit 0 : ALWAYS. This hook must never block or delay work, so there is no `set -e` and
#            every step is defensive; a broken logger degrades to silence, not denial.
#            (Logging deliberately hangs off postToolUse, not fail-closed preToolUse.)
#
# jq is optional but recommended: without it the args/result split is impossible, so the raw
# scan counts every path mention as a LOAD (discovery folds into usage — degraded but joinable).
set -uo pipefail

event="${1:-unknown}"
payload="$(cat 2>/dev/null || true)"

# Repo root: hooks run with cwd=.claude/hooks; prefer git (worktree-safe), fall back to ../..
root="$(git rev-parse --show-toplevel 2>/dev/null)" || root=""
[ -n "$root" ] || root="$(cd ../.. 2>/dev/null && pwd)" || root="$PWD"

have_jq=0; command -v jq >/dev/null 2>&1 && have_jq=1

jqs() {  # jqs <jq-expr> — extract a string field from $payload, empty on any failure
  [ "$have_jq" = 1 ] || { echo ""; return 0; }
  printf '%s' "$payload" | jq -r "$1 // empty" 2>/dev/null || true
}

session="$(jqs '.sessionId // .session_id')"
[ -n "$session" ] || session="${CLAUDE_AUDIT_SESSION:-${COPILOT_AUDIT_SESSION:-unknown}}"
# Launcher-provided role/ticket/prompt capture: CLAUDE_* names; COPILOT_* still honoured.
audit_role="${CLAUDE_AUDIT_ROLE:-${COPILOT_AUDIT_ROLE:-}}"
audit_ticket="${CLAUDE_AUDIT_TICKET:-${COPILOT_AUDIT_TICKET:-}}"
audit_prompts="${CLAUDE_AUDIT_PROMPTS:-${COPILOT_AUDIT_PROMPTS:-}}"
# session id becomes a filename — keep it path-safe even if the payload is hostile/garbled
session="$(printf '%s' "$session" | tr -cd 'A-Za-z0-9._-' | cut -c1-64)"
[ -n "$session" ] || session="unknown"

ts="$(jqs '(.timestamp // empty) | tostring')"
logged_at="$(date -u +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || echo '')"
tool="$(jqs '.toolName // .tool_name')"
agent_evt="$(jqs '.agent_type // .agentName // .agent_name')"

dir="$root/.apm-audit"
mkdir -p "$dir/sessions" "$dir/state" 2>/dev/null || exit 0
log="$dir/sessions/${session}.jsonl"
stack="$dir/state/${session}.agents"

# --- agent attribution -------------------------------------------------------------------
# preToolUse/postToolUse carry no agent identity, so track it: subagentStart pushes the
# agentName on a per-session stack, subagentStop pops it. Between those, the acting agent is
# the top of the stack; outside any subagent it is the role the launcher exported
# (CLAUDE_AUDIT_ROLE, set by scripts/run-role.sh) or "main". Parallel subagents in one
# session would interleave here — the raw AGENT_START/STOP records keep that visible.
case "$event" in
  subagentStart) [ -n "$agent_evt" ] && printf '%s\n' "$agent_evt" >> "$stack" 2>/dev/null ;;
  subagentStop)  [ -s "$stack" ] && sed -i '$d' "$stack" 2>/dev/null ;;
esac
agent="$(tail -n 1 "$stack" 2>/dev/null || true)"
# Claude Code stamps agent_type on every event fired inside a subagent: on a tool event it is
# authoritative and beats the stack (which parallel subagents interleave).
case "$event" in postToolUse|postToolUseFailure) [ -n "$agent_evt" ] && agent="$agent_evt" ;; esac
[ -n "$agent" ] || agent="${audit_role:-main}"

esc() {  # esc <text> — JSON-string-escape (quotes, backslashes, control chars stripped)
  printf '%s' "$1" | tr -d '\000-\037' | sed -e 's/\\/\\\\/g' -e 's/"/\\"/g'
}

emit() {  # emit <type> <extra-json-fields (already quoted, comma-led or empty)>
  printf '{"type":"%s","event":"%s","session":"%s","agent":"%s","ts":"%s","loggedAt":"%s"%s}\n' \
    "$1" "$event" "$(esc "$session")" "$(esc "$agent")" "$(esc "$ts")" "$logged_at" "$2" \
    >> "$log" 2>/dev/null
}

json_arr() {  # json_arr [name...] — emit a JSON array of escaped strings
  local out="" n
  for n in "$@"; do out="${out:+$out,}\"$(esc "$n")\""; done
  printf '[%s]' "$out"
}

skill_names() {  # skill_names <text> — unique skill names whose SKILL.md path appears in text
  # No prefix before "skills": a greedy prefix class would let one match span several paths
  # in a blob (e.g. an ls result), swallowing all but the last name.
  printf '%s' "$1" \
    | grep -oE 'skills[\\/]+[A-Za-z0-9_-]+[\\/]+SKILL\.md' 2>/dev/null \
    | sed -E 's#skills[\\/]+([A-Za-z0-9_-]+)[\\/]+SKILL\.md#\1#' | sort -u || true
}

instr_names() {  # instr_names <text> — unique rule basenames (.claude/rules/*.md; legacy *.instructions.md)
  printf '%s' "$1" \
    | grep -oE '(rules[\\/]+[A-Za-z0-9._-]+\.md|instructions[\\/]+[A-Za-z0-9._-]+\.instructions\.md)' 2>/dev/null \
    | sed -E 's#^(rules|instructions)[\\/]+##' | sort -u || true
}

doc_names() {  # doc_names <text> — unique repo-relative docs/**.md paths appearing in text
  # Unlike skill/instruction names, a doc path must allow '/', so the greedy-span hazard the
  # skill_names comment warns about bites twice here: in JSON-stringified payloads a Windows
  # separator arrives as \\ and a newline as \n, and a class containing both '\' and '/' would
  # run straight through them, welding adjacent paths into one. Normalize first — collapse
  # \\ to /, blank the remaining single-char escapes — then match with a backslash-free class.
  # Same no-prefix trait as skill_names (an "apidocs/x.md" matches from "docs/" onward);
  # acceptable for observability, and stamp() quietly no-ops on paths that don't exist.
  printf '%s' "$1" \
    | sed -e 's#\\\\#/#g' -e 's#\\[ntrbf]# #g' \
    | grep -oE 'docs/[A-Za-z0-9._/-]+\.md' 2>/dev/null \
    | sed -E 's#//+#/#g' | sort -u || true
}

stamp() {  # stamp <repo-relative-path> — set commit= last-touch short sha, dirty= true/false
  commit=""; dirty="false"
  if [ -f "$root/$1" ]; then
    commit="$(git -C "$root" log -1 --format=%h -- "$1" 2>/dev/null || echo '')"
    git -C "$root" diff --quiet -- "$1" 2>/dev/null || dirty="true"
  fi
}

case "$event" in
  sessionStart)
    # Join keys for the report: the commit the session ran on + the deployed-set lockfile stamp.
    head_sha="$(git -C "$root" rev-parse --short HEAD 2>/dev/null || echo '')"
    branch="$(git -C "$root" rev-parse --abbrev-ref HEAD 2>/dev/null || echo '')"
    lock_at="$(sed -n "s/^generated_at: *'\{0,1\}\([^']*\)'\{0,1\}$/\1/p" "$root/apm.lock.yaml" 2>/dev/null | head -n1)"

    # TICKET — the join key everything else hangs off. It used to come only from
    # COPILOT_AUDIT_TICKET, which only scripts/run-role.sh sets, so a session started with a bare
    # `copilot` recorded "" and became unqueryable: the audit found ALL EIGHT SESSION_START records
    # carrying an empty ticket, and `audit-report.sh --ticket PROJ-1406` returning "no sessions match"
    # against files that mention PROJ-1406 seven times. The trail was complete and useless.
    #
    # The branch name already encodes it and is already read one line above, so derive it when the
    # env var is absent: feature/PROJ-1406-mask-id-in-logs, PROJ-1406/part-domain, bugfix/proj-99 all
    # yield the id. Explicit env always wins — a deliberate --ticket must be able to override a
    # branch that says otherwise (a hotfix cut from the wrong branch, a worktree reused).
    ticket="$audit_ticket"
    ticket_src="env"
    if [ -z "$ticket" ] && [ -n "$branch" ]; then
      ticket="$(printf '%s' "$branch" | grep -oiE '[A-Z][A-Z0-9]+-[0-9]+' | head -n1 | tr '[:lower:]' '[:upper:]' || true)"
      [ -n "$ticket" ] && ticket_src="branch"
    fi
    [ -n "$ticket" ] || ticket_src="none"

    # ENTRYPOINT — how the session was launched. Without this an unattributed session is
    # indistinguishable from one legitimately running as "main", so "429 of 431 records say
    # agent:main" cannot be read as either a tooling gap or a real fact. Recording it makes the
    # difference visible instead of inferred: "raw" means nobody set a role, and any per-role
    # analysis of that session is measuring nothing.
    entrypoint="raw"; [ -n "$audit_role" ] && entrypoint="run-role"

    emit "SESSION_START" ",\"role\":\"$(esc "$audit_role")\",\"ticket\":\"$(esc "$ticket")\",\"ticketSource\":\"$(esc "$ticket_src")\",\"entrypoint\":\"$(esc "$entrypoint")\",\"headSha\":\"$(esc "$head_sha")\",\"branch\":\"$(esc "$branch")\",\"lockGeneratedAt\":\"$(esc "$lock_at")\",\"cwd\":\"$(esc "$(jqs '.cwd')")\""

    # SCOPE: what this checkout (repo or pruned part worktree) actually offers the session —
    # the deployed skill set + the instruction files. This becomes the "scoped into the
    # worktree" column of the per-agent report.
    sk=(); in_=()
    if [ -d "$root/.claude/skills" ]; then
      while IFS= read -r d; do [ -n "$d" ] && sk+=("$d"); done \
        < <(ls -1 "$root/.claude/skills" 2>/dev/null | sort)
    fi
    for f in "$root/.claude/rules"/*.md; do
      [ -f "$f" ] && in_+=("$(basename "$f")")
    done
    # docs denominator: the code-maps tree only — the framework-owned docs whose usage the
    # report should account for. Other docs/ reads still log as DOC_LOAD/SEEN, just unscoped.
    dm=()
    if [ -d "$root/docs/code-maps" ]; then
      while IFS= read -r f; do [ -n "$f" ] && dm+=("$f"); done \
        < <(cd "$root" && find docs/code-maps -name '*.md' 2>/dev/null | tr '\\' '/' | sort)
    fi
    emit "SCOPE" ",\"skills\":$(json_arr ${sk[@]+"${sk[@]}"}),\"instructions\":$(json_arr ${in_[@]+"${in_[@]}"}),\"docs\":$(json_arr ${dm[@]+"${dm[@]}"})"
    ;;
  userPrompt)
    # PROMPT TEXT IS NOT STORED BY DEFAULT.
    #
    # This trail lives in a regulated repo, and a prompt is the least predictable field in it: it
    # is whatever the operator typed, which in practice has included personal identifiers,
    # ticket context, pasted logs and credential hints ("try it with my keyring"). Storing that
    # verbatim on disk turns an observability file into a data-protection surface — one careless
    # `git add -A` publishes it, and unlike every other field here it can never be justified as
    # necessary, because nothing consumes it: scripts/audit-report.sh does not read `prompt` at all.
    #
    # What the report DOES need from this event is a join key and a way to tell two sessions apart.
    # A truncated SHA-256 gives both — identical prompts collide by design, which is the useful
    # property — without keeping the content. Length is kept because "was this the one-liner or the
    # 4KB paste" is the question a reconstruction actually asks.
    #
    # CLAUDE_AUDIT_PROMPTS=raw restores the old behaviour for a debugging session. It is an env var
    # on the launching process, deliberately not a hooks.env key: opting into storing user text
    # should be a per-session act by a human, not a setting a repo drifts into and forgets.
    raw="$(jqs '.prompt')"
    chars="$(printf '%s' "$raw" | wc -m 2>/dev/null | tr -cd '0-9')"; chars="${chars:-0}"
    sha=""
    if command -v sha256sum >/dev/null 2>&1; then
      sha="$(printf '%s' "$raw" | sha256sum 2>/dev/null | cut -c1-16)"
    elif command -v shasum >/dev/null 2>&1; then
      sha="$(printf '%s' "$raw" | shasum -a 256 2>/dev/null | cut -c1-16)"
    fi
    if [ "$audit_prompts" = "raw" ]; then
      emit "PROMPT" ",\"capture\":\"raw\",\"promptChars\":${chars},\"promptSha\":\"$(esc "$sha")\",\"prompt\":\"$(esc "$(printf '%s' "$raw" | cut -c1-200)")\""
    else
      emit "PROMPT" ",\"capture\":\"redacted\",\"promptChars\":${chars},\"promptSha\":\"$(esc "$sha")\""
    fi
    ;;
  subagentStart)
    emit "AGENT_START" ",\"agentName\":\"$(esc "$agent_evt")\",\"transcript\":\"$(esc "$(jqs '.transcriptPath // .transcript_path')")\""
    ;;
  subagentStop)
    emit "AGENT_STOP" ",\"agentName\":\"$(esc "$agent_evt")\",\"stopReason\":\"$(esc "$(jqs '.stopReason // .stop_reason')")\""
    ;;
  sessionEnd)
    emit "SESSION_END" ",\"reason\":\"$(esc "$(jqs '.reason')")\""
    rm -f "$stack" 2>/dev/null
    ;;
  postToolUse|postToolUseFailure)
    # Tool summary: never store toolResult (can be megabytes) — just the tool + a short arg hint.
    arg="$(jqs '(.tool_input // .toolArgs // {}) as $a | $a.command // $a.file_path // $a.path // $a.pattern // ($a|tostring)' | cut -c1-200)"
    okflag="true"; [ "$event" = "postToolUseFailure" ] && okflag="false"
    emit "TOOL" ",\"tool\":\"$(esc "$tool")\",\"arg\":\"$(esc "$arg")\",\"ok\":$okflag"

    # READ vs DISCOVERED: a path in the tool ARGS is an explicit open (the body entered
    # context) → *_LOAD. A path only in the tool RESULT scrolled past the agent (ls / grep /
    # file-search output) without being opened by this call → *_SEEN. Without jq the two
    # can't be separated, so everything counts as a LOAD (degraded mode, header note).
    if [ "$have_jq" = 1 ]; then
      args_text="$(jqs '(.tool_input // .toolArgs // {}) | tostring')"
      result_text="$(jqs '(.tool_response // .toolResult // .tool_result // {}) | tostring')"
    else
      args_text="$payload"; result_text=""
    fi

    loads="$(skill_names "$args_text")"
    for skill in $loads; do
      sp=".claude/skills/${skill}/SKILL.md"
      [ -f "$root/$sp" ] || sp="skills/${skill}/SKILL.md"
      stamp "$sp"
      emit "SKILL_LOAD" ",\"skill\":\"$(esc "$skill")\",\"skillPath\":\"$(esc "$sp")\",\"skillCommit\":\"$(esc "$commit")\",\"dirty\":$dirty"
    done
    for skill in $(skill_names "$result_text"); do
      printf '%s\n' "$loads" | grep -qx "$skill" && continue   # opened in this same call → already a LOAD
      emit "SKILL_SEEN" ",\"skill\":\"$(esc "$skill")\""
    done

    iloads="$(instr_names "$args_text")"
    for instr in $iloads; do
      case "$instr" in *.instructions.md) stamp ".github/instructions/${instr}" ;; *) stamp ".claude/rules/${instr}" ;; esac
      emit "INSTRUCTION_LOAD" ",\"instruction\":\"$(esc "$instr")\",\"instructionCommit\":\"$(esc "$commit")\",\"dirty\":$dirty"
    done
    for instr in $(instr_names "$result_text"); do
      printf '%s\n' "$iloads" | grep -qx "$instr" && continue
      emit "INSTRUCTION_SEEN" ",\"instruction\":\"$(esc "$instr")\""
    done

    dloads="$(doc_names "$args_text")"
    for d in $dloads; do
      stamp "$d"
      emit "DOC_LOAD" ",\"doc\":\"$(esc "$d")\",\"docCommit\":\"$(esc "$commit")\",\"dirty\":$dirty"
    done
    for d in $(doc_names "$result_text"); do
      printf '%s\n' "$dloads" | grep -qx "$d" && continue
      emit "DOC_SEEN" ",\"doc\":\"$(esc "$d")\""
    done

    # Persona loads: an agent body read (.claude/agents/<role>.md) is context too.
    personas="$(printf '%s' "$args_text" \
      | grep -oE 'agents[\\/]+[A-Za-z0-9_-]+(\.agent)?\.md' 2>/dev/null \
      | sed -E 's#agents[\\/]+([A-Za-z0-9_-]+)(\.agent)?\.md#\1#' | sort -u || true)"
    for p in $personas; do
      emit "PERSONA_LOAD" ",\"persona\":\"$(esc "$p")\""
    done
    ;;
  *)
    emit "EVENT" ""
    ;;
esac

exit 0
