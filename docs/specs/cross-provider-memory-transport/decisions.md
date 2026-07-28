# Cross-Provider Memory Transport — Decisions

**Provenance:** Drafted by Claude Fable 5 on 2026-07-22 from the live
Codex-sandbox and host-side diagnosis recorded in `requirements.md`.
Roundtable thread `q-cross-provider-memory-spec-review-001`; chair approved
promotion candidates `#6`, `#7`, and `#8` on 2026-07-22.

All decisions below are **RATIFIED**.

## D1 — MCP-first for sandboxed clients — RATIFIED

- **Options:** (a) MCP-first, with Python only in trusted host contexts;
  (b) keep Python-first and improve errors; (c) build a generic bridge.
- **Recommendation:** (a). MCP already passed the Codex canary and does not
  weaken the sandbox. A new bridge duplicates the intended MCP boundary.
- **Falsified if:** a required client cannot expose Attune MCP. That client
  uses the honest degraded tier from D2; it does not invalidate MCP-first
  where MCP exists.

## D2 — Capability tiers rather than parity fiction — RATIFIED

- **Options:** (a) explicit MCP, hooks + MCP, and unsupported/degraded tiers;
  (b) advertise uniform best-effort support.
- **Recommendation:** (a). Codex has no lifecycle hooks today. Promising
  automatic capture there would repeat the silent-failure pattern.
- **Falsified if:** Codex gains verified lifecycle hooks; its matrix row then
  upgrades without changing the architecture.

## D3 — Add `session_memory_*` tools for the verified semantics gap — RATIFIED

- **Options:** (a) reuse `redis_memory_*`; (b) add thin provider-neutral
  adapters; (c) make agents compose raw store + promote.
- **Decision:** (b). The review verified that raw `redis_memory_store` is a
  generic working-memory path and does not preserve the complete
  sanitization, cwd, and TTL contract. Option (c) is rejected because
  agent-side composition will drift.

### D3 execution evidence — T2 measurement (2026-07-22)

Re-measured against the live tree before building (spec-scope-vs-code
rule). The semantics gap is real and the verdict stands:

- `redis_memory_store` → `AMSMemoryBackend.stash()` — key/value
  working memory. No sanitization call, no cwd tagging, no
  session-stash TTL semantics on that path.
- `session_stash.stash_entry()` is the only chokepoint carrying the
  full contract (sanitize → truthful write → type/cwd topics), so the
  five `session_memory_*` adapters delegate there (option b, as
  ratified). No existing Redis tool was duplicated; the six
  `redis_memory_*` schemas are pinned by a freeze test.
- **CR-2 canary found a live bug:** the PII gate was a silent no-op —
  `DataSanitizer()` constructor defaults disable both scrubbers, so an
  email passed to the stored representation unredacted (every prior
  unit test mocked the gate). Fixed in T2: both gates explicitly
  enabled; secrets fail closed (write refused). Non-mocked regression
  tests now pin redaction and refusal through the public
  `stash_entry()` boundary and through real MCP dispatch.
- Boolean-to-MCP mapping (CR-5): Python `False` surfaces as
  `{ok: false, reason: <stable_code>}` — codes `no_backend`,
  `file_write_denied`, `write_failed`, `invalid_entry`, `not_found`,
  `internal_error`, `session_stash_unavailable`.
- **Live AMS receipt (R8 #3, host, 2026-07-22):** through the real
  `session_memory_*` handlers against the resolved `AMSMemoryBackend`
  (status `reachable`, transport `mcp`/`direct`): capture ok →
  recall hit on attempt 1 with stored representation
  `"T2-LIVE-CANARY-e5f1: contact [EMAIL] re parser deadlock"` (the
  PII-bearing canary redacted in AMS) → forget deleted 1 →
  re-recall found nothing. Canary cleaned up; cleanup confirmed.

## D4 — Caller-scoped reachability — RATIFIED

- **Options:** (a) `reachable`, `unreachable_local`, `unknown`; (b) boolean
  up/down.
- **Recommendation:** (a). The diagnosed bug was a caller-local block
  misreported as a Redis failure.
- **Falsified if:** no consumer uses the distinction after one release; then
  simplify without restoring false global claims.

## D5 — File fallback returns false after failed durable write — RATIFIED

- **Options:** (a) return `False` and expose an additive reason; (b) raise;
  (c) keep returning `True` and log.
- **Recommendation:** (a). The API is intentionally never-raises, while (c)
  is the verified data-loss bug.
- **Falsified if:** caller audit proves exception classes are required. In
  that case, exceptions stay inside the backend and the public wrapper still
  returns a truthful result.

## D6 — Preserve existing Redis MCP contracts — RATIFIED

- **Options:** (a) freeze existing signatures and add tools if required;
  (b) extend existing tools in place.
- **Recommendation:** (a). These are public plugin surfaces; additive tools
  avoid breaking consumers.
- **Falsified if:** a required semantic cannot be expressed additively; any
  extension then requires versioning and a changelog entry.

## D7 — Live boundary matrix is the completion gate — RATIFIED

## Roundtable revision ruling — RATIFIED

- **CR-1 / board #6:** public `stash_entry()` propagates durable-write
  failure and receives an EPERM regression at that boundary.
- **CR-2 / board #7:** finding capture uses sanitized
  `session_memory_capture`; raw `redis_memory_*` remains generic working
  memory; a PII-bearing live canary proves sanitization.
- **CR-3–CR-6 / board #8:** add changelog coverage, complete status-consumer
  compatibility checks, explicit boolean-to-MCP result mapping, and cleanup
  plus a sandbox JSON example for the file-writability probe.

- **Options:** (a) the six receipts in R8; (b) mocked tests only.
- **Recommendation:** (a). This spec exists because green local logic did not
  prove the real boundary.
- **Falsified if:** a provider cannot be run. Record an honest unsupported or
  unprobed receipt; never substitute a synthetic pass.

## 2026-07-28 — Status flipped to `shipped`; CHAIR_REQUIRED discharged

Chair-ruled on promotion of round-table thread
`routine-clean-run-20260728-1020` (report:
`docs/reports/roundtable/routine-clean-run-20260728-1020.md`). That
thread's appendix triaged this spec as item 1; two of three seats read
it as CLOSE-as-shipped, and the third's hold was traced to reading the
declared status string rather than PR/receipt state — the stale label
this entry retires.

**Evidence the flip rests on** (verified at flip time, not inferred):

| Receipt | Result |
|---|---|
| 1 File-write-failure regression | PASS |
| 2 Real MCP dispatch | PASS |
| 3 AMS round-trip + PII canary | PASS (live) |
| 4 Codex live MCP canary | PASS (live) |
| 5 Claude Code hook canary | PASS (live) |
| 6 Antigravity/Gemini probe | PASS (live, 10.6.1) |

Held stack lifted 2026-07-27: T1 #1593, T2 #1594, T3 #1596, T5 #1598 —
all MERGED, each re-targeted to main before its base branch was
deleted, per the tasks.md procedure.

The `chair-review:cross-provider-memory-transport` ledger entry is a
soft (exit 1) boundary marker, not a technical blocker — this status
flip is what discharges it.

**Correction to the appendix's framing:** it referred to "the five
phase files." Only THREE carry a `**Status:**` line (`requirements.md`,
`design.md`, `tasks.md`); `decisions.md` and `receipts.md` have none by
construction. All three are flipped.
