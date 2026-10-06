---
name: bean-config-di
description: Wire collaborators with Spring @Configuration classes and constructor injection. Use when configuring DI.
---
# Bean configuration & dependency injection

> **Generic "how" only.** No concrete bean/config-class names in the body — those live in the code-map.

## When to use
Wiring a collaborator (client, gateway, cache, scheduler) into the Spring context, or choosing an
implementation per environment.

## How
- Declare beans in dedicated `@Configuration` classes; keep wiring **out of** domain/use-case code.
- Prefer **constructor injection** (final fields); avoid field injection. Let components be discovered
  where idiomatic, but centralize non-trivial wiring (clients, third-party beans) in config classes.
- Scope environment-specific beans with `@Profile`; disambiguate multiples with `@Qualifier`/`@Primary`.
- Externalize values with `@Value`/`@ConfigurationProperties`; never inline endpoints/secrets.
- Keep config classes thin — they assemble, they don't compute.

## Pattern signals (discovery cues)
`@Configuration` classes with `@Bean` factory methods; constructor-injected `final` collaborators;
`@Profile`/`@Qualifier`/`@Primary`; `@ConfigurationProperties`/`@Value` for externalized config.

## Project specifics → see docs
- Code map (config classes, profiles, properties conventions) → `docs/code-maps/bean-config-di.md` *(per-repo map, written by the pattern-scanner — resolves once harvested)*

## Guardrails (what NOT to do)
- Don't wire beans inside domain/use-case classes — that's the config layer's job.
- Don't use field injection; constructor-inject final fields.
- Don't hardcode env-specific values — externalize and profile them.

## Definition of done
- [ ] Collaborators wired in `@Configuration` via constructor injection; env variants profiled/qualified; values externalized; no wiring in business code.
- [ ] Verified by: the application context loading in a slice test, and no business class importing the DI framework's injection annotation.
