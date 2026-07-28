# Cross-Provider Memory Transport — Requirements

**Status:** APPROVED — implementation authorized 2026-07-22.
**Slug:** `cross-provider-memory-transport`

## Problem

Redis-backed short-term memory works from trusted host contexts but
silently fails from sandboxed providers. In Codex, the recall skill's
plain-Python recipe runs inside a network- and write-restricted sandbox:
`backend_status()` selects `FileStashBackend` with
`unreachable_upgrade=redis` (localhost blocked), and `stash_entry()` hits
`file_stash_write_failed: Operation not permitted` yet returns `True`.
The canary never reaches AMS and recall returns nothing — a false-success
data-loss path.

## Verified state (2026-07-22 receipts)

- Codex sandbox: Python selects the file backend; its write fails;
  `remember()` still returns `True`; no canary is recalled.
- Host: Redis PING succeeds, AMS 0.14.0 `/v1/health` returns 200,
  `AMSMemoryBackend` is selected, and stash → semantic recall → cleanup
  succeeds.
- Codex already has Attune MCP tools: `redis_health_check` returned
  `connected=true`; `redis_memory_store` → `redis_memory_retrieve`
  round-tripped an exact canary; the disposable session was deleted.
- Root cause: the recall skill's sandboxed-Python recipe plus an
  unwritable file fallback that reports success — not a Redis outage.
  No new generic bridge is needed.

## Goal

Provide consistent, truthful short-term memory across Codex, Claude Code,
Antigravity/Gemini, and future clients by routing capture and recall over
each client's real capabilities, without weakening sandbox security or
creating a second memory subsystem.

## Requirements

### R1 — Truthful file fallback

`FileStashBackend` write failures must surface as failure.

- `_rewrite()` must return whether the durable replace succeeded, and
  `remember()` must return `False` after an `OSError`.
- The public `session_stash.stash_entry()` boundary must propagate the
  backend's durable-write result; it must not convert `False` back to success.
- `backend_status()` must expose an additive machine-readable reason such
  as `file_write_denied` when writability is known to have failed.
- A regression test simulates `EPERM` on the temporary file through the
  public `stash_entry()` API and asserts a false write result plus the
  status/log reason.
- No path may report success without a durable write. False success is
  forbidden.

### R2 — No global-outage inference from local denial

Caller-local sandbox denial must be distinct from a verified service-down
state.

- Additive status fields distinguish `reachable`, `unreachable_local`, and
  `unknown` while preserving the existing `backend`, `fallback`, and
  `unreachable_upgrade` keys.
- Documentation and skills must never claim "Redis is down" from a
  sandboxed probe alone.

### R3 — MCP-first transport

When Attune MCP tools are available, capture and recall route through MCP
(host-side execution), not in-process sandboxed Python. Direct Python
remains valid for trusted host contexts such as lifecycle hooks and CLI.

### R4 — Provider-neutral session operations, only if needed

The verified `redis_memory_*` calls are generic working-memory operations;
they do not preserve the complete `session_stash` sanitization, cwd, and TTL
contract. Add narrow `session_memory_*` MCP tools that delegate to
`session_stash`. Finding-capture flows must use `session_memory_capture`,
never raw `redis_memory_store`, and agents must not compose raw operations to
emulate a stash write.

- Schemas are narrow, content and results bounded, inputs validated, and
  credentials excluded.
- The tools are memory operations, not an arbitrary filesystem or network
  proxy.

### R5 — Honest capability tiers

- MCP clients receive explicit capture and recall.
- Hook-capable clients such as Claude Code may additionally receive
  automatic session-start recall and session-end capture.
- Clients with neither receive a clear `unsupported` or `degraded` result.
- Codex currently executes no `hooks.json` hooks; this spec must not promise
  automatic end-of-session capture there.

### R6 — Backward compatibility

Existing `redis_memory_*` tools retain their signatures and behavior.
The `session_stash` Python API remains compatible for host callers except
that failed writes now honestly return `False`. Status changes are additive.

### R7 — Semantics preserved

PII/secrets sanitization, cwd soft-priority, the 30-day working TTL,
user-gated promotion to curated memory, and precise deletion apply on every
transport.

### R8 — Boundary receipts

Completion requires real receipts, with every canary cleaned up:

1. File-write-failure regression returns `False` and exposes the reason.
2. Real MCP dispatch exercises updated or new handlers.
3. Disposable AMS capture → search → forget succeeds, including a
   PII-bearing canary whose stored form proves sanitization.
4. Codex completes a live MCP canary.
5. Claude Code completes a live hook canary.
6. Antigravity/Gemini produces a capability receipt or an honest
   unsupported receipt.

## Provider capability matrix

| Client | MCP tools | Lifecycle hooks | Python context | Supported tier |
|---|---|---|---|---|
| Claude Code | yes | yes | trusted host | hooks + MCP |
| Codex | yes (verified) | no | sandbox blocks network/write | explicit MCP |
| Antigravity/Gemini | probe required | no | assume restricted | MCP or unsupported |
| Unknown future client | unknown | unknown | assume restricted | capability-driven; degraded by default |

## Non-goals

- No second memory subsystem; reuse `session_stash`, `FileStashBackend`,
  and `AMSMemoryBackend`.
- No generic sandbox-to-host network bridge or proxy.
- No reopening `docs/specs/archive/claude-cross-session-memory/`.

## Done state

Codex captures and recalls through MCP with exact-canary receipts; the
Claude Code hook flow remains unchanged and re-verified; file fallback never
lies; the recall skill routes by capability; Antigravity/Gemini has a real
probe or documented unsupported status; all R8 receipts are recorded and all
canaries deleted.
