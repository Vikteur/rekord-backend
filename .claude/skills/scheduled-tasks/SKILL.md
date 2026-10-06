---
name: scheduled-tasks
description: Idempotent, multi-instance-safe scheduled background jobs. Use when adding cron or fixed-rate work.
---
# Scheduled background tasks

> **Generic "how" only.** No concrete job/schedule values in the body — those live in the code-map.

## When to use
Periodic background work — cache warming, polling, cleanup, refresh — that runs on a timer rather than
in response to a request.

## How
- Annotate a method `@Scheduled(cron=… | fixedDelay=…)` on a config/component bean; enable scheduling once.
- Make the task **idempotent** — it may run again after a failure or on multiple instances.
- **Guard for multi-instance** deployments (a lock / leader election / "only-one-runs" flag) so a job
  doesn't double-execute across replicas.
- Keep the scheduled method thin: delegate to a use-case; catch + log failures so one bad run doesn't
  kill the schedule.
- Make it observable (log start/finish + outcome); externalize the cadence to config.

## Pattern signals (discovery cues)
`@Scheduled` methods; `@EnableScheduling`; cadence from `@Value`/properties; a guard/lock for
multi-instance; the method delegating to a use-case.

## Project specifics → see docs
- Code map (the scheduled jobs, cadences, guards) → `docs/code-maps/scheduled-tasks.md` *(per-repo map, written by the pattern-scanner — resolves once harvested)*

## Guardrails (what NOT to do)
- Don't assume a single instance — guard against concurrent runs across replicas.
- Don't let an exception escape and silently stop the schedule — catch + log.
- Don't bury business logic in the scheduled method — delegate to a use-case.

## Definition of done
- [ ] `@Scheduled` thin entry delegating to a use-case; idempotent; multi-instance guarded; cadence externalized; failures logged, schedule survives.
- [ ] Verified by: a test invoking the scheduled method twice and asserting the second run is a no-op, plus the arch-fitness rule pairing the scheduling and batch-logging annotations staying green.
