#!/usr/bin/env bash
# arch-fitness.sh — Claude Code `SubagentStop` gate (advisory): the blueprint's **arch-fitness** check, local half.
#
# templates/hooks-and-gates.md stages `arch-fitness` (backend ArchUnit) / `fe-arch-fitness` (frontend
# dependency-cruiser) as a gate. THIS hook is the workstation half: the instant a code-writing subagent
# finishes a part, it runs the boot-free layer-purity check, so a domain→adapter or framework-in-domain
# violation is caught in-loop instead of only on the PR. Deterministic and boot-free (static ArchUnit /
# dependency-cruiser — no Spring context), so it runs on the workstation even though the heavy test
# suite is offloaded to CI.
#
# NOTE ON THE CI HALF: in the central repo `arch-fitness` also ran in `agentic-quality.yml → archTest`,
# but that workflow is removed from consumers by the migration (`migration/README.md`), and its
# replacement `migration/consumer-ci/agentic-gates.yml` runs no `archTest`. In the target consumer
# state this hook is therefore the SOLE enforcement unless that repo wires a fitness step into its own
# build CI — same caveat `lint-format` carries, and the reason ARCH_FITNESS_CMD being unset is worth
# noticing rather than shrugging at.
#
# Unlike the observability hooks (always exit 0), this is a GATE: a non-zero exit bounces the part back.
# The concrete command is per-repo config in hooks.env (this blueprint is generic):
#
#   ARCH_FITNESS_CMD   e.g. ./gradlew archTest   (backend)  /  npx depcruise src   (frontend)
#
# Unset → informative no-op, so the scaffold ships safely before a repo supplies its fitness task.
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

export GATE_NAME=arch-fitness
# shellcheck source=/dev/null
. "$(cd "$(dirname "$0")" && pwd)/gate-common.sh"

# Fail CLOSED on anything that stops the gate from doing its job (see lint-format.sh).
root="$(gate_repo_root)" || exit 1
cd "$root" || { echo "::error::[arch-fitness] cannot cd to repo root '$root'"; exit 1; }

# Order is deliberate: GATE_AGENTS comes OUT of hooks.env, so the config must load before the agent
# filter can honour a repo's override. The cost is that a skipping role still parses the file (and may
# print a warning about it) before deciding it has nothing to do — cheap, and worth it. Do not swap.
gate_load_env "$root"                 # parses .claude/hooks/hooks.env; never sources it
gate_should_run "$payload" || exit 0  # not a code-writing role → no layers were touched

cmd="${ARCH_FITNESS_CMD:-}"
if [ -z "$cmd" ]; then
  echo "[arch-fitness] not configured (ARCH_FITNESS_CMD unset) — skipping the boot-free layer-boundary"
  echo "[arch-fitness] check. Set ARCH_FITNESS_CMD (e.g. \"./gradlew archTest\" or \"npx depcruise src\")"
  echo "[arch-fitness] in .claude/hooks/hooks.env to enforce it. See README.md."
  exit 0
fi

echo "[arch-fitness] running: $cmd   (ARCH_FITNESS_CMD $(gate_origin ARCH_FITNESS_CMD))"
bash -c "$cmd"; rc=$?
if [ "$rc" -ne 0 ]; then
  echo "::error::[arch-fitness] FAILED (exit $rc) — an architecture fitness rule failed. The part goes back"
  echo "          to its developer (do not accept it). See templates/hooks-and-gates.md."
  exit "$rc"
fi
echo "[arch-fitness] PASSED — the configured fitness rules hold."
exit 0
