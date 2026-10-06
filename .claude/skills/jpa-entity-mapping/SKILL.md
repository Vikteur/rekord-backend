---
name: jpa-entity-mapping
description: JPA entities kept separate from the domain and mapped at the repository edge. Use for a persisted type.
---
# JPA entity mapping

> **Generic "how" only.** No concrete entity/table names in the body — those live in the code-map.

## When to use
Adding or changing a persisted, table-backed type — the JPA `@Entity` that the persistence adapter
reads/writes.

## How
- Keep the `@Entity` in the **adapter/persistence layer**, separate from the domain aggregate; map
  between them in the repository ([[persistence-repository]]). The domain stays JPA-free.
- Annotate explicitly: `@Entity`, `@Table`, `@Id` + generation, `@Column` (names/nullability), relations
  with explicit fetch types (default to LAZY for collections).
- Match the schema owned by migrations ([[flyway-migrations]]); don't let Hibernate auto-DDL drive prod.
- Keep entities behavior-light (persistence shape, not business rules — those live in the domain).
- Be deliberate about `equals/hashCode` (id-based) and avoid mapping you don't query.

## Pattern signals (discovery cues)
`@Entity`/`@Table`/`@Id`/`@Column` classes in the adapter/persistence layer; explicit fetch types;
a separate domain type with a mapper between them; schema from migrations, not auto-DDL.

## Project specifics → see docs
- Code map (entity exemplars, relation/fetch conventions) → `docs/code-maps/jpa-entity-mapping.md` *(per-repo map, written by the pattern-scanner — resolves once harvested)*

## Guardrails (what NOT to do)
- Don't reuse a JPA `@Entity` as the domain type — keep them separate.
- Don't rely on auto-DDL for production schema — migrations own it.
- Don't put business logic on entities.

## Definition of done
- [ ] `@Entity` in the persistence layer, explicit mappings + fetch types, schema from migrations, mapped to a distinct domain type; id-based equality.
- [ ] Verified by: a repository slice test against a container database whose schema comes from the migrations, not from auto-DDL.
