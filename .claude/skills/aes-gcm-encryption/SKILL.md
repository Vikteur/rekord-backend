---
name: aes-gcm-encryption
description: Encrypt sensitive strings with AES/GCM and an externalized key. Use when storing or transmitting PII.
---
# AES/GCM string encryption

> **Generic "how" only.** No key property names, key length, service/class names, or field names in
> the body — those live in the code-map leaf.

## When to use
You must store or transmit a sensitive string (a personal identifier, token, or other PII) such that
it is encrypted at rest or in flight and recoverable by the same service. Encrypt on write/output,
decrypt on read/input.

## How
- Use authenticated symmetric encryption: `AES/GCM/NoPadding` with a fixed auth-tag length (128 bits).
  GCM gives confidentiality *and* integrity in one pass — prefer it over CBC/ECB.
- Generate a fresh random IV for **every** message from a `SecureRandom` (12 bytes is the GCM standard).
  Never reuse an IV with the same key — IV reuse breaks GCM catastrophically.
- Frame the output so decrypt is self-describing: prepend the IV to the ciphertext, then Base64-encode
  the whole buffer. On decrypt, slice the leading IV bytes off, then decrypt the remainder.
- Externalize the key (injected config / secrets manager), never hard-code it. Build the `SecretKey`
  once at construction and reuse it; keep the same byte encoding (UTF-8) on both sides.
- Handle null/blank inputs explicitly (pass through), and on failure throw a typed exception — but log
  errors without dumping the plaintext or the key.

## Pattern signals (discovery cues)
`Cipher.getInstance("AES/GCM/NoPadding")`, `GCMParameterSpec`, a `SecureRandom`-filled IV byte array
with a "never reuse" comment, IV prepended to ciphertext before Base64, a `SecretKeySpec` built from an
injected/externalized key, and paired `encrypt`/`decrypt` methods on a small utility/service.

## Project specifics → see docs
- Code map (utility class, key source, IV/tag sizes, call sites, exemplars) → `docs/code-maps/aes-gcm-encryption.md` *(per-repo map, written by the pattern-scanner — resolves once harvested)*

## Guardrails (what NOT to do)
- Don't reuse an IV with the same key, and don't derive the IV deterministically — always random.
- Don't hard-code or log the key, and don't log the plaintext on an exception path.
- Don't use ECB/CBC or unauthenticated modes for sensitive data — GCM gives integrity too.
- Don't invent a custom framing; prepend-IV-then-Base64 keeps encrypt/decrypt symmetric.

## Definition of done
- [ ] AES/GCM with a per-message random IV and 128-bit tag; IV prepended and the whole thing Base64-encoded;
  key injected from externalized config; null/blank handled; failures throw a typed exception without
  leaking secrets; a round-trip test (and ideally a tamper-detection test) passes.
