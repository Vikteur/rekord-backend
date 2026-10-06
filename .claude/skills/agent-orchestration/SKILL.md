---
name: agent-orchestration
description: Run a lean-context multi-agent pipeline. Use when orchestrating agents.
---
# Agent orchestration

> **Generic "how" only.** Zero project nouns (no package roots, tags, config keys, artifact
> filenames). Concrete role→model routing, artifact locations, and hook names live in the code-map
> leaf, referenced below. See `ARCHITECTURE.md` §1 (blueprint repo).

## When to use
Driving a multi-agent workflow — you hold the whole task and hand slices to specialist agents. When
the question is *who gets what context, in what order, on which model*. This is the orchestrator's core loop.

## How
- **Scope each agent to only what it needs** — its role, its inputs, its done-check. Never pour the
  whole task into a sub-agent; a narrow prompt is cheaper and sharper.
- **Slice large artifacts.** Hand a per-layer / per-tag slice, never a whole plan or spec. A script
  extracts the slice so the agent reads one relevant excerpt, not the document.
- **One full-reader per artifact.** Exactly one agent reads the whole plan, one the whole spec;
  everyone else gets slices. Avoids N agents each paying to re-read the same big file.
- **Push deterministic work to hooks/scripts** — formatting, codegen, lint, extraction. Zero-context
  mechanical steps don't belong in an agent prompt.
- **Summary handoffs, not diffs.** Pass files-changed + green status forward, not the full diff — the
  next agent needs the outcome, not the keystrokes.
- **Order context system → stable → volatile-last** so the cacheable prefix stays byte-identical and
  prompt caching hits; put the one thing that changes per call at the end.
- **Route by difficulty.** Mechanical/structural roles → a cheaper model; hard reasoning/judgment
  roles → the top model. Match model cost to the role, not to the whole pipeline.

## Pattern signals (discovery cues — how the scanner recognizes this in any codebase)
- A multi-agent config: named agent/role definitions, per-role prompt templates, a driver/pipeline script.
- Slice/extract scripts that pull a per-layer or per-tag excerpt from a larger artifact.
- Hooks or CI steps owning deterministic work (format, codegen, lint) outside any prompt.
- Per-role model routing (a role→model map) and a stable-prefix prompt layout for caching.

## Project specifics → see docs
- Code map (role→model routing, artifact/slice locations, hook names) → `docs/code-maps/agent-orchestration.md` *(per-repo map, written by the pattern-scanner — resolves once harvested)*

## Guardrails (what NOT to do)
- Don't hand an agent a whole plan or spec — slice it; the single full-reader is the only exception.
- Don't pass diffs between agents when a files-changed + status summary carries the outcome.
- Don't run deterministic work inside a prompt when a hook/script can do it context-free.
- Don't reorder the cacheable prefix per call — volatile content goes last or caching misses.
- Don't route a hard-reasoning role to the cheap model, or waste the top model on mechanical work.

## Definition of done
- [ ] Each agent scoped to its role + inputs; large artifacts sliced, one full-reader each.
- [ ] Deterministic steps live in hooks/scripts; handoffs are summaries, not diffs.
- [ ] Context ordered system → stable → volatile-last; roles routed to the right-cost model.
