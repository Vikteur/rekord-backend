---
name: spring-caching
description: Cache read-heavy results and evict on mutation, with per-cache TTL. Use when a read repeats expensive work.
---
# Spring caching

> **Generic "how" only.** No cache names, TTL values, cache-manager provider, or property keys in the
> body — those live in the code-map leaf.

## When to use
A read method does expensive or remote work whose result is stable for a while and its inputs repeat:
reference data, access matrices, translations, remote lookups. Add `@Cacheable`; evict on writes.

## How
- Enable caching once (`@EnableCaching` on a config class), then annotate read methods with
  `@Cacheable("<cacheName>")`. Use a `key` SpEL expression when the cached value depends on method
  arguments; add `unless`/`condition` to skip caching error-shaped or empty results.
- Invalidate on every mutation: put `@CacheEvict(value = "<cacheName>", allEntries = true)` on
  save/delete methods so the cache can't serve stale data. Pair eviction with the same cache name the
  reads use — a typo silently disables invalidation.
- Configure each named cache explicitly: TTL (time-to-live) or max-idle, an eviction policy (e.g. LRU),
  and a bounded max size. One config entry per cache, tuned to how that data changes — not one global
  default. Externalize TTLs that differ by environment via injected config values.
- Cache at the right boundary: read-heavy, slow, or remote lookups whose inputs repeat. Don't cache
  fast in-process calls or per-request unique data.

## Pattern signals (discovery cues)
`@EnableCaching` on a config class; `@Cacheable` / `@CacheEvict` annotations on repository/gateway
methods; a cache-manager config bean declaring named caches with per-cache TTL/eviction/size; tests
that swap in an in-memory cache manager whose cache names match the annotations exactly.

## Project specifics → see docs
- Code map (cache manager, named caches + TTLs, evicting mutations, test config, exemplars) → `docs/code-maps/spring-caching.md` *(per-repo map, written by the pattern-scanner — resolves once harvested)*

## Guardrails (what NOT to do)
- Don't add `@Cacheable` to a read without a matching `@CacheEvict` on its mutations — stale data.
- Don't cache failures or empty fallbacks as if they were real results — guard with `unless`.
- Don't reference a cache name that isn't declared in the cache-manager config.
- Don't cache user-specific data under a shared key — scope the key to the identifying argument.

## Definition of done
- [ ] Read is `@Cacheable` under a declared, configured cache (TTL + eviction + bound); every mutation
  evicts the same cache; error/empty results aren't cached; a test proves a second call hits the cache
  and a mutation invalidates it.
