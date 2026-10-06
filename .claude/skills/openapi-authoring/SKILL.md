---
name: openapi-authoring
description: Hand-author the shared OpenAPI spec — operationIds, components, tags, lint-gated. Use when editing the spec.
---
# OpenAPI authoring

> **Generic "how" only.** No spec filenames, security-scheme keys, header names, tag names, enum
> values, or product/tool names in the body — those live in the code-map leaf.

## When to use
Authoring or evolving a hand-written OpenAPI spec that is the single shared source of truth for an
API — consumed downstream by generated clients and server stubs in separate repos. Use when adding or
changing an operation, schema, parameter, security scheme, or tag, where the spec is the contract and
must stay lintable and backward-compatible.

## How
- Treat the spec as the one canonical artifact: edit it by hand, keep it the single source of truth,
  and let consumers (clients, server stubs) regenerate from it downstream — never the reverse.
- Give every operation a stable, unique `operationId`: downstream codegen names methods from it, so a
  missing or renamed id breaks or churns generated code. Treat it as part of the public contract.
- Make every request and response body carry a complete schema (typed properties, required lists,
  formats) — no untyped or empty bodies, so generated models are usable.
- Declare every path-template variable as a `required: true` path parameter with a schema; never leave
  a `{var}` in a path undeclared.
- Factor shared pieces into `components` and `$ref` them everywhere: one reusable security scheme, the
  common cross-cutting header parameters (request context, response locale/language), and shared error
  responses, param families, and schemas — define once, reference many.
- Apply the security scheme globally (top-level `security`) so every operation is protected by default;
  override per-operation only for the deliberate exceptions.
- Maintain a tag taxonomy that mirrors capability domains, and separate public/end-user-facing tags from
  privileged/admin tags so the audience of each operation is explicit and consistently named.
- Gate the spec in CI with a lint ruleset (the base OpenAPI ruleset plus project-specific rules such as
  "request/response bodies need a schema", "operationId required", "path params declared") — the spec
  must lint clean before merge.
- Evolve backward-compatibly: diff each change against the published baseline (the contract on the main
  line) with a breaking-change diff, and keep changes additive — new optional fields, new operations,
  widened responses. Route any genuinely breaking change through an explicit, gated decision
  (versioning / deprecation), never silently into the shared contract.

## Pattern signals (discovery cues)
A single hand-authored OpenAPI/Swagger document tracked as the canonical artifact (not generated); a
lint config that extends the base OpenAPI ruleset and adds custom rules keyed on operations/schemas;
CI that runs the lint and a breaking-change diff of the PR spec against the main-branch baseline; a
`components` block with a reusable security scheme applied via top-level `security`, shared header
parameters, and shared error/param/schema definitions `$ref`-ed across operations; a tag list pairing
public/end-user domains with privileged/admin counterparts.

## Project specifics → see docs
- Code map (spec location, lint ruleset + custom rules, security scheme, shared headers/params, tag
  taxonomy, breaking-change gate, exemplars) → `docs/code-maps/openapi-authoring.md` *(per-repo map, written by the pattern-scanner — resolves once harvested)*

## Guardrails (what NOT to do)
- Don't ship an operation without a unique `operationId`, or rename one casually — both break/churn
  downstream codegen.
- Don't leave a request/response body or a path parameter without a schema.
- Don't inline a security scheme, header, error response, or shared schema you could `$ref` from
  `components`.
- Don't introduce a breaking change into the shared contract — keep edits additive and let the
  breaking-change diff gate enforce it; version or deprecate instead.
- Don't hand-edit or commit generated client/server code into this repo — the spec is the only source.

## Definition of done
- [ ] Every new/changed operation has a unique `operationId`, complete request/response schemas, and
  declared required path params; shared pieces are `$ref`-ed from `components`; tags fit the
  public/admin taxonomy; the spec lints clean against the ruleset; and the breaking-change diff against
  the published baseline reports additive-only (or the break is explicitly versioned/deprecated).
