---
name: flyway-migrations
description: Versioned, forward-only SQL migrations applied on startup. Use when changing the database schema.
---
# Flyway migrations

> **Generic "how" only.** No concrete table names or version numbers in the body — those live in the code-map.

## When to use
Any schema change (new table/column, index, constraint, data backfill) in a project where the schema is
owned by versioned migrations applied on startup.

## How
- **STOP for human approval before a migration lands** — post the SQL, the affected tables and the
  rollback story, then wait. Applied on startup and forward-only means there is no undo: the moment
  it runs against an environment holding real records, a wrong `DROP`, a mistyped `NOT NULL` on a
  populated column, or a backfill with a bad `WHERE` is permanent. This is the one-way door the
  general STOP rule names, and no test suite closes it — a migration that destroys production data
  passes CI, because CI runs it against an empty database.
- Add a new file `V<n>__short_description.sql` in the migration location; **never edit an already-applied
  migration** — append a new version (migrations are immutable once shipped).
- Keep versions strictly increasing and unique; one logical change per file.
- Make migrations forward-only and idempotent where feasible; prefer additive changes; sequence
  destructive steps (add → backfill → switch → drop) across releases.
- Match the production database's dialect; test migrations against a real instance ([[testcontainers]]).
- Keep repeatable (`R__`) migrations for views/functions separate from versioned ones.

## Pattern signals (discovery cues)
A `db/migration` resource folder with `V<n>__*.sql` (and `R__*.sql`); a migration tool on the classpath;
strictly increasing version prefixes; no edits to historical files.

## Project specifics → see docs
- Code map (migration location, naming, dialect, exemplars) → `docs/code-maps/flyway-migrations.md` *(per-repo map, written by the pattern-scanner — resolves once harvested)*

## Guardrails (what NOT to do)
- Don't apply a migration on your own judgment — a human approves the SQL before it lands.
- Don't modify a migration that has already run anywhere — add a new version.
- Don't reuse or skip version numbers.
- Don't do a destructive drop in the same release as the code that still reads the column.

## Definition of done
- [ ] New `V<n>__…` file, unique increasing version, immutable history; tested against a real DB; destructive changes staged across releases; **the SQL was approved by a human before it landed**.
