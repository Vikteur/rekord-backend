---
name: domain-events
description: Publish framework-free domain events through a port so side-effects react via listeners. Use for event-driven work.
---
# Domain Events

> **Generic "how" only.** Zero project nouns. Concrete event types, the publisher port, its adapter
> and the listeners live in the code-map docs leaf, referenced below. See `ARCHITECTURE.md` §1 (blueprint repo).

## When to use
Adding a side-effect that should fire when a domain fact occurs (indexing, notifying, projecting,
cache eviction) without coupling the originating logic to that side-effect or to the framework.

## How
- Define a **marker event interface** in the inner layer — a plain empty type all events implement.
  The domain depends only on this marker, never on a framework event base class.
- Model each event as an **immutable value** (a record) named in the **past tense** ("what happened",
  e.g. `*Created` / `*Updated` / `*Deleted`) carrying just the facts a handler needs.
- **Publish through a port**: an interface (owned inside) with a single `publish(event)` method. The
  use-case depends on this port, not on any framework event bus.
- Implement the port **once at the edge** with an adapter that delegates to the framework's event
  mechanism. This is the only place that knows the framework.
- **Subscribe with listeners at the edge**, one handler per side-effect; keep them thin — translate
  the event into a call on the relevant collaborator. Side-effects never live in the publisher.
- Publish **after the state change is committed/valid** (only on the success path), so listeners never
  react to work that was rejected or rolled back; bind listeners to the originating transaction when
  the side-effect must share its fate.

## Pattern signals (discovery cues — how the scanner recognizes this in any codebase)
- A marker `*Event` interface in an inner package with **no framework imports**.
- Event types as past-tense records implementing that marker.
- A publisher **port interface** inside + a single adapter implementing it over the framework bus.
- Edge listeners/handlers subscribing to event types, one per side-effect.
- Use-cases depending on the publisher port, never on a framework `ApplicationEventPublisher`-style type.

## Project specifics → see docs
- Code map (marker interface, event types, publisher port + adapter, listeners, exemplars) → `docs/code-maps/domain-events.md` *(per-repo map, written by the pattern-scanner — resolves once harvested)*

## Guardrails (what NOT to do)
- Don't make domain events extend or import a framework event type — keep the marker framework-free.
- Don't publish a framework-specific type directly from a use-case; go through the port.
- Don't put side-effect logic in the publisher — that belongs in listeners.
- Don't publish before the change is valid/committed (avoid acting on rolled-back work).

## Definition of done
- [ ] Marker event interface is framework-free; events are past-tense immutable values.
- [ ] Publishing is behind a port; one edge adapter bridges to the framework bus.
- [ ] Side-effects live in thin listeners; events published only on the committed success path.
- [ ] Verified by: a domain-layer test passing with no framework event type on the classpath, and a listener test asserting the side-effect fires only after commit.
