#!/usr/bin/env bash
# verify-claims.sh — Claude Code `SubagentStop` gate (advisory): an agent that reports "part complete" must
# have actually changed something, and the change must land inside the files it was told to touch.
#
# WHY THIS EXISTS. Every other check in this system reads what the agent *says*. `developer.agent.md`
# deliberately returns "files changed … **not the diff**" (token rule #5), the reviewer judges code
# against the AC rather than the narrative, and CI runs by SHA. All of that is correct — and all of it
# is downstream of one unverified premise: that the agent wrote the files it claims. It is the single
# most-repeated failure in practice ("The Trust Fall" / "Hallucinated Edits"): an agent reports every
# replacement applied, and the file has zero changes because the writes went to a temp copy, or to a
# path outside the worktree, or never happened. A summary-only handoff makes that *invisible* — there
# is no diff anywhere in the pipeline for a human or a later agent to notice it in.
#
# So this gate does not read the claim at all. It reads the work tree. `subagentStop` is the only
# event that fires exactly when an agent asserts completion, and it carries `agent_type`. (In
# Claude Code exit 1 only reports; exit 2 would make the subagent keep working — see README.)
#
# TWO CHECKS, in order of how badly they fail:
#
#   1. NON-EMPTY  — the union of (uncommitted changes) and (commits since the part's base) must not
#                   be empty. An empty union with a "done" claim is a hallucinated edit, full stop.
#   2. IN-SCOPE   — if the part's Declared Files are resolvable, at least one changed path must be
#                   inside them. This catches the subtler variant: real writes, wrong tree. It is a
#                   *some*, not an *only*: a part legitimately touches build files, test fixtures and
#                   generated resources that no plan enumerates, so requiring every path to be
#                   declared would bounce honest work. Requiring at least one proves the agent was
#                   in the right place.
#
# Framework scaffolding is excluded from both: `apm install` rewrites `.claude/skills/`,
# `.claude/agents/`, `.claude/rules/` (or their .github/ equivalents) and `apm.yml` on every worktree re-scope, so counting
# those would let an agent pass this gate by having done nothing at all. Same exclusion list
# `worktree-consumer.sh` uses for its dirty check, and for the same reason.
#
# CONFIG (hooks.env, both optional):
#   VERIFY_CLAIMS_BASE      ref the part forked from. Default: resolved from the branch name —
#                           `feature/<ticket>/part-<layer>-<cap>` -> the shared `feature/<ticket>-*`
#                           branch, else origin/HEAD's default branch, else origin/main, else main.
#   VERIFY_CLAIMS_DECLARED  path to this part's plan file; its `- Declared Files:` field is read via
#                           scripts/plan-slice.sh. Unset -> check 2 is skipped, loudly.
#
# DIRECTION OF FAILURE. Fail closed on "the agent did nothing"; fail open on "this gate cannot tell".
# An unresolvable base, a detached HEAD, a missing plan file — none of those are evidence of a bad
# agent, and bouncing every part in a repo whose refs are shaped differently would get the gate
# deleted within a day. Every degraded path prints WHY it degraded, because a silent skip here is
# indistinguishable from a pass and this gate exists precisely to kill that class of ambiguity.
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

export GATE_NAME=verify-claims
# shellcheck source=/dev/null
. "$(cd "$(dirname "$0")" && pwd)/gate-common.sh"

# Fail CLOSED on anything that stops the gate from doing its job (see lint-format.sh).
root="$(gate_repo_root)" || exit 1
cd "$root" || { echo "::error::[verify-claims] cannot cd to repo root '$root'"; exit 1; }

# Order is deliberate: GATE_AGENTS comes OUT of hooks.env (see lint-format.sh). Do not swap.
gate_load_env "$root"                 # parses .claude/hooks/hooks.env; never sources it
gate_should_run "$payload" || exit 0  # not a code-writing role → it claimed no code

branch="$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo '')"

# ── Resolve the part's base ──────────────────────────────────────────────────────────────────────
# Only used for the COMMITTED half of the union. A wrong-but-existing base makes this gate stricter
# (fewer commits counted), never laxer, because the uncommitted half is measured independently.
ref_exists() { git rev-parse --verify --quiet "$1^{commit}" >/dev/null 2>&1; }

base="${VERIFY_CLAIMS_BASE:-}"
base_src="hooks.env/env"
if [ -n "$base" ] && ! ref_exists "$base"; then
  echo "[verify-claims] VERIFY_CLAIMS_BASE='$base' does not resolve to a commit — falling back."
  base=""
fi
if [ -z "$base" ]; then
  base_src="derived"
  # feature/<ticket>/part-<layer>-<cap> → the shared feature branch this part forked from.
  case "$branch" in
    feature/*/part-*)
      ticket="${branch#feature/}"; ticket="${ticket%%/*}"
      for cand in $(git for-each-ref --format='%(refname:short)' \
                      "refs/heads/feature/${ticket}-*" "refs/remotes/*/feature/${ticket}-*" 2>/dev/null); do
        ref_exists "$cand" && { base="$cand"; break; }
      done
      ;;
  esac
fi
if [ -z "$base" ]; then
  # origin/HEAD is the honest answer for "the default branch" and survives a repo that renamed it.
  head_ref="$(git symbolic-ref --quiet --short refs/remotes/origin/HEAD 2>/dev/null || true)"
  for cand in "$head_ref" origin/main origin/master main master; do
    [ -n "$cand" ] || continue
    ref_exists "$cand" && { base="$cand"; break; }
  done
fi

# ── Collect the changed set ──────────────────────────────────────────────────────────────────────
# Scaffolding `apm install` rewrites on every re-scope. Anchored at the start so a real source file
# whose path merely CONTAINS one of these strings is not silently forgiven.
is_scaffolding() {
  case "$1" in
    .claude/agents/*|.claude/rules/*|.claude/skills/*|\
    .github/agents/*|.github/instructions/*|.github/skills/*|apm.yml|\
    .apm-audit/*|.codegraph/*) return 0 ;;
  esac
  return 1
}

changed_raw=""

# Uncommitted (tracked + untracked). Two flags carry weight here:
#   -z      a real-world repo has paths with spaces, and `--porcelain`'s quoting of them would
#           otherwise arrive as a literal `"…"` that matches nothing.
#   -uall   without it git COLLAPSES an untracked directory to one entry (`?? .claude/skills/`), which the
#           scaffolding filter below — written against file paths — does not match. A fresh worktree
#           whose only change is `apm install` laying down `.claude/skills/` then reads as one real
#           changed file and PASSES. That is precisely the "did nothing" case this gate exists for,
#           so the collapsed form is not a cosmetic difference.
while IFS= read -r -d '' entry; do
  # porcelain -z: `XY <path>`, and for R/C a second NUL-separated field follows that we do not need
  # (the destination is what a later record reports anyway).
  changed_raw="${changed_raw}${entry:3}"$'\n'
done < <(git status --porcelain -z --untracked-files=all 2>/dev/null || true)

# Committed since the base. `...` (symmetric) not `..`: with `..` a stale base ref that has moved
# ahead reports the BASE's commits as this part's work — the exact false pass this gate exists to
# prevent.
if [ -n "$base" ]; then
  while IFS= read -r p; do
    [ -n "$p" ] && changed_raw="${changed_raw}${p}"$'\n'
  done < <(git diff --name-only "${base}...HEAD" 2>/dev/null || true)
else
  echo "[verify-claims] no base ref resolved (branch '$branch') — only UNCOMMITTED work counts."
  echo "[verify-claims] Set VERIFY_CLAIMS_BASE in .claude/hooks/hooks.env if this repo's part"
  echo "[verify-claims] branches fork from something other than the default branch."
fi

changed=""
while IFS= read -r p; do
  [ -n "$p" ] || continue
  is_scaffolding "$p" && continue
  changed="${changed}${p}"$'\n'
done < <(printf '%s' "$changed_raw" | sort -u)

# ── Check 1: the agent changed something at all ──────────────────────────────────────────────────
if [ -z "$changed" ]; then
  echo "::error::[verify-claims] FAILED — this agent reported completion, but the repository is"
  echo "          unchanged. No uncommitted edits, and no commits since"
  echo "          '${base:-<no base resolved>}'. Framework scaffolding (.claude/skills,"
  echo "          .claude/agents, .claude/rules, their .github/ twins, apm.yml) is excluded."
  echo "          Either the writes went somewhere other than this work tree (a temp copy, a path"
  echo "          outside the worktree, a different checkout), or they never happened. Re-do the"
  echo "          part and verify with 'git status' before reporting done."
  echo "          branch=$branch  base=${base:-none} (${base_src})"
  exit 1
fi

n_changed="$(printf '%s' "$changed" | grep -c . || true)"
echo "[verify-claims] ${n_changed} file(s) changed vs base '${base:-none}' (${base_src})."

# ── Check 2: the change landed inside the part's Declared Files ──────────────────────────────────
plan="${VERIFY_CLAIMS_DECLARED:-}"
if [ -z "$plan" ]; then
  echo "[verify-claims] scope check SKIPPED — VERIFY_CLAIMS_DECLARED is unset, so this gate cannot"
  echo "[verify-claims] tell whether the changes are in the right place, only that they exist. Point"
  echo "[verify-claims] it at the part's plan file in .claude/hooks/hooks.env to close that half."
  echo "[verify-claims] PASSED (non-empty only)."
  exit 0
fi
if [ ! -f "$plan" ]; then
  echo "[verify-claims] scope check SKIPPED — VERIFY_CLAIMS_DECLARED='$plan' does not exist."
  echo "[verify-claims] PASSED (non-empty only)."
  exit 0
fi

slicer="$root/scripts/plan-slice.sh"
if [ ! -f "$slicer" ]; then
  echo "[verify-claims] scope check SKIPPED — scripts/plan-slice.sh not found, cannot read the"
  echo "[verify-claims] '- Declared Files:' field of '$plan'."
  echo "[verify-claims] PASSED (non-empty only)."
  exit 0
fi

declared_block="$(bash "$slicer" "$plan" --declared 2>/dev/null || true)"
if [ -z "$declared_block" ]; then
  echo "[verify-claims] scope check SKIPPED — '$plan' has no '- Declared Files:' field."
  echo "[verify-claims] PASSED (non-empty only)."
  exit 0
fi

# Pull path-shaped tokens out of the prose bullet. Backticked first (the documented shape); if the
# plan writes them bare, fall back to anything containing a '/' with a file extension. Deliberately
# permissive — a missed declared path only weakens check 2 toward the check-1 baseline, whereas an
# over-eager parse would bounce honest work.
declared="$(printf '%s\n' "$declared_block" \
  | grep -oE '`[^`]+`' 2>/dev/null | tr -d '`' | grep -E '/' || true)"
if [ -z "$declared" ]; then
  declared="$(printf '%s\n' "$declared_block" \
    | grep -oE '[A-Za-z0-9_./-]+/[A-Za-z0-9_./-]+\.[A-Za-z0-9]+' 2>/dev/null || true)"
fi
if [ -z "$declared" ]; then
  echo "[verify-claims] scope check SKIPPED — no path-shaped entries in the Declared Files field of"
  echo "[verify-claims] '$plan'."
  echo "[verify-claims] PASSED (non-empty only)."
  exit 0
fi

# A declared entry may be a file or a directory prefix; match either. Normalise both sides so a
# leading ./ or a Windows separator does not read as a different path.
norm() { local p="${1//\\//}"; p="${p#./}"; printf '%s' "${p%/}"; }

hit=""
while IFS= read -r c; do
  [ -n "$c" ] || continue
  cn="$(norm "$c")"
  while IFS= read -r d; do
    [ -n "$d" ] || continue
    dn="$(norm "$d")"
    if [ "$cn" = "$dn" ] || case "$cn" in "$dn"/*) true ;; *) false ;; esac; then
      hit="$cn"; break 2
    fi
  done <<< "$declared"
done <<< "$changed"

if [ -z "$hit" ]; then
  echo "::error::[verify-claims] FAILED — this agent changed ${n_changed} file(s), but NONE of them"
  echo "          are inside its Declared Files. The work exists but landed outside this part's"
  echo "          boundary, which is either the wrong tree or scope creep into another part."
  echo "          Declared (from '$plan'):"
  printf '%s\n' "$declared" | sed 's/^/          - /'
  echo "          Changed:"
  printf '%s' "$changed" | sed 's/^/          - /'
  exit 1
fi

echo "[verify-claims] PASSED — real changes, inside the Declared Files (e.g. '$hit')."
exit 0
