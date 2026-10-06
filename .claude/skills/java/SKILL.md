---
name: java
description: Idiomatic modern Java — immutability, Optional, records, streams. Use when writing or reviewing Java.
---
# Java

> **Generic "how" only.** Zero project nouns. The JDK version, build tool, and project idioms live
> in the code-map docs leaf, referenced below. See `ARCHITECTURE.md` §1 (blueprint repo).

## When to use
Writing or reviewing Java in any layer. Pairs with [[clean-code]] (general) and [[clean-architecture]]
(placement); this skill is the language-idiom layer.

## How
- Prefer **immutability**: `final` fields, `record` for data carriers, unmodifiable collections.
- Model closed hierarchies with **sealed** types; exhaustively switch over them.
- Return **`Optional`** instead of `null` for "maybe absent"; never `Optional` fields/params.
- **try-with-resources** for anything `AutoCloseable`; never swallow exceptions — wrap with context.
- Use the **streams API** for clear transformations, but drop to loops when it reads better; avoid
  side effects inside streams.
- Favor constructor injection and final dependencies; keep nullability at the boundary, not inside.
- Equality/identity: value types override `equals`/`hashCode` (records do this for you).

## Pattern signals (discovery cues — how the scanner recognizes this in any codebase)
- `*.java` sources; a `pom.xml` / `build.gradle(.kts)` with a JDK toolchain.
- Use of `record`, `sealed`, `Optional`, `var`, `switch` expressions → modern-Java baseline.
- Lombok or MapStruct annotations (project idiom), constructor-injection style.

## Project specifics → see docs
- Code map (JDK version, build tool, allowed libs, project idioms, exemplars) → `docs/code-maps/java.md` *(per-repo map, written by the pattern-scanner — resolves once harvested)*

## Guardrails (what NOT to do)
- Don't return or accept `null` where `Optional`/empty-collection is meaningful.
- Don't catch-and-ignore; don't catch `Exception`/`Throwable` broadly without rethrow.
- Don't leak mutable internal collections from getters.

## Definition of done
- [ ] Idiomatic, mostly-immutable code; no raw nulls across boundaries.
- [ ] Resources closed; exceptions carry context.
- [ ] Compiles clean with no new warnings.
