---
name: soap-cxf-gateway
description: Apache CXF SOAP client with WSDL codegen and WS-Security/STS. Use for outbound SOAP integrations.
---
# SOAP gateway with Apache CXF + WS-Security

> **Generic "how" only.** No endpoint URLs, service names, or keystore paths in the body — those live
> in the code-map leaf.

## When to use
Integrating an external SOAP service — especially one requiring WS-Security (signed/encrypted bodies,
SAML tokens from a Security Token Service, mutual TLS).

## How
- Generate the client stubs from the WSDL at build time (CXF `wsdl2java` / codegen plugin); keep the
  generated sources out of hand-edits.
- Build the port via a `JaxWsProxyFactoryBean` (or generated service); register **out-interceptors**
  for WS-Security: sign with the client key, encrypt to the server cert, attach the STS-issued SAML
  token. Keep keystore/truststore config externalized.
- For STS: request the SAML token with an `STSClient`; cache it for its lifetime; refresh before expiry.
- Translate SOAP faults into typed domain/gateway exceptions at the boundary; never leak the raw fault.
- Put the call behind a circuit breaker + cache where appropriate (see [[resilience4j]] / [[spring-caching]]).

## Pattern signals (discovery cues)
`cxf-spring-boot-starter-jaxws` / `cxf-rt-ws-security` deps; `wsdl2java` codegen; `JaxWsProxyFactoryBean`;
`WSS4JOutInterceptor` / `STSClient`; keystore + truststore config; classes named `*SoapGateway` / `*WebServiceConfig`.

## Project specifics → see docs
- Code map (services, STS/security config, decryption, exemplars) → `docs/code-maps/soap-cxf-gateway.md` *(per-repo map, written by the pattern-scanner — resolves once harvested)*

## Guardrails (what NOT to do)
- Don't hand-edit generated WSDL stubs — regenerate.
- Don't hardcode secrets/keystore passwords — externalize to a secret store.
- Don't log full SOAP envelopes in production (they carry sensitive payloads + identifiers).

## Definition of done
- [ ] Client generated from WSDL; WS-Security interceptors wired; STS token cached/refreshed; faults mapped
  to typed exceptions; an integration test stubs the endpoint and verifies a signed request + parsed response.
