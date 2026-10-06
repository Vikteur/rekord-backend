---
name: openapi-rest-client-codegen
description: Generate a typed REST client from an OpenAPI spec at build time. Use when calling an API that ships a spec.
---
# OpenAPI REST client codegen

> **Generic "how" only.** No service names, spec filenames, package roots, header names, or property
> keys in the body — those live in the code-map leaf.

## When to use
Integrating with an external HTTP service that publishes an OpenAPI spec, instead of hand-writing the
client. Generate typed API + model classes at build time, then wire base path, auth, and headers onto
a shared HTTP client.

## How
- Add the OpenAPI generator plugin to the module build; point `inputSpec` at the vendored spec file.
  Pick the generator and a modern HTTP library (e.g. the framework's native rest-client), and target a
  dedicated `apiPackage` / `invokerPackage` so generated code never collides with hand-written code.
- Narrow the output: select only the APIs/models you use, switch off generated tests and supporting
  files, set a model name suffix, and enable the Jakarta/EE option to match the runtime.
- Make codegen part of the build graph: emit into the build output dir, add it as a source root, and
  make compilation depend on the generate task so the client is always regenerated and never committed.
- Wire the client at composition time: build the generated `ApiClient` over a shared, pre-configured
  HTTP client, set the base path from config, and attach auth via a default header (API key) or a
  request interceptor (bearer token, content negotiation). Expose each generated `*Api` as a bean.
- Keep secrets and base paths externalized (config properties / injected values), never inline.

## Pattern signals (discovery cues)
An OpenAPI/Swagger generator plugin in the build with `inputSpec` / `apiPackage` / `invokerPackage`;
a vendored spec file under the module's resources; a generated-sources dir added to the source set and
a compile task depending on the generate task; a config class building an `ApiClient` over a shared
HTTP client and registering `*Api` beans with interceptors or default headers for auth.

## Project specifics → see docs
- Code map (generator config, spec locations, client wiring, exemplars) → `docs/code-maps/openapi-rest-client-codegen.md` *(per-repo map, written by the pattern-scanner — resolves once harvested)*

## Guardrails (what NOT to do)
- Don't commit generated client code — generate it on every build and gitignore the output dir.
- Don't hand-edit generated classes; change the spec or generator config instead.
- Don't inline API keys, tokens, or base paths — inject them from externalized config.
- Don't build a fresh HTTP client per gateway when a shared/proxy-aware one exists — mutate it.

## Definition of done
- [ ] The client is generated from the spec at build time into a non-committed source root; only the used
  APIs/models are emitted; each `*Api` is a bean over a shared HTTP client with auth wired via header
  or interceptor; base path and secrets come from config; the module compiles from a clean checkout.
