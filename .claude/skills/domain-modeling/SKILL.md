---
name: domain-modeling
description: Framework-free entities and value objects with invariants enforced in a factory. Use when changing a domain type.
---
# Domain Modeling

> **Generic "how" only.** Zero project nouns. Concrete entities, factories, validators and the
> creation-result helper live in the code-map docs leaf, referenced below. See `ARCHITECTURE.md` §1 (blueprint repo).

## When to use
Adding a new domain entity or value object, introducing creation rules / invariants, or refactoring
an anaemic data holder into a real domain type. The core modelling skill for the inner layer.

## How
- Keep the domain **framework-free**: no persistence, web, DI or transaction imports — plain language
  types only. The domain must compile and be testable with no container.
- Make fields **final**; set them once at construction. Expose getters, not blanket setters. State
  changes happen through intention-revealing methods (`grant`, `update`, `revoke`), never field pokes.
- **Construct through a factory**, not a public constructor: the constructor stays package-private and
  the factory is the single creation entry point, so an instance cannot exist in an invalid shape.
- Pass creation inputs as a dedicated **create-request / input object**, not a long positional arg list.
- **Enforce invariants where the object is born**: the entity validates itself (required fields,
  cross-field rules, allowed transitions) and the factory returns the object *together with* the
  validation outcome — accumulate problems, don't throw on the first one.
- Model true value objects as **immutable, equality-by-value** (a record or value-equality type);
  reserve identity-based equality for entities with a real identifier.
- Put behaviour **next to the data it guards**: a rule about an entity's fields belongs on that entity.

## Pattern signals (discovery cues — how the scanner recognizes this in any codebase)
- Inner-layer packages (`domain`) with **no framework imports**; only language + small util libs.
- Entities with `final` fields, a non-public constructor, and a paired `*Factory` creating them.
- A `validate()` method on the entity returning an accumulated result rather than throwing.
- A `Create*Request` / input object feeding the constructor; a `Creation`/result wrapper bundling
  value + validation.
- Value objects expressed as records or equality-by-value types.

## Project specifics → see docs
- Code map (entities, factories, create-requests, validators, creation-result helper, exemplars) → `docs/code-maps/domain-modeling.md` *(per-repo map, written by the pattern-scanner — resolves once harvested)*

## Guardrails (what NOT to do)
- Don't import a framework/persistence/web type into a domain class (hook: archunit/dependency gate).
- Don't expose a public constructor or open setters that let callers bypass invariants.
- Don't throw on the first validation error when the caller expects all problems at once.
- Don't scatter the same rule across callers — keep it on the entity/factory.

## Definition of done
- [ ] Entity is framework-free; fields final; created only via its factory.
- [ ] Invariants enforced at construction; validation outcome returned with the object.
- [ ] Value objects immutable with value equality; behaviour sits with its data.
- [ ] Verified by: a factory test in which every invariant rejects its own violation, and the domain module compiling with no framework dependency declared.
