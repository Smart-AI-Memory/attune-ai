# Cross-Provider Memory Transport — R8 Receipts

Dated ledger for the six R8 boundary receipts. Every diagnostic canary
is deleted after its receipt; a synthetic or mocked provider pass is
forbidden (D7). Honest `UNPROBED` rows stay until the named client
actually runs.

| # | Receipt | Status | Date |
|---|---------|--------|------|
| 1 | File-write-failure regression | PASS | 2026-07-22 |
| 2 | Real MCP dispatch | PASS | 2026-07-22 |
| 3 | AMS round-trip + PII canary | PASS (live) | 2026-07-22 |
| 4 | Codex live MCP canary | UNPROBED (blocked pre-lift) | 2026-07-22 |
| 5 | Claude Code hook canary | PASS (live) | 2026-07-22 |
| 6 | Antigravity/Gemini probe | UNPROBED (recon done) | 2026-07-22 |

## 1 — File-write-failure regression (T1, held #1593)

`tests/unit/memory/test_file_stash.py::
test_eperm_through_public_stash_entry_returns_false` — simulated
`EPERM` on the temp file through public `stash_entry()`: returns
`False`, `file_stash_write_failed` reason visible in logs,
`backend_status()` reports `reachability: unreachable_local` with
`reason: file_write_denied` from a real write probe. No canary to
clean (tmp-path fixture).

## 2 — Real MCP dispatch (T2, held #1594)

`tests/integration/test_mcp_dispatch.py::TestSessionMemoryDispatch` —
`call_tool → _dispatch_tool → _plugin_handlers` on a real
`EmpathyMCPServer` with the attune_redis tools actually registered;
only the storage backend is substituted, the REAL sanitizer runs.
Covers capture → recall → forget round-trip, PII redaction in the
stored representation, and `{ok: false, reason: no_backend}` mapping.

## 3 — Disposable AMS capture → search → forget (live, 2026-07-22)

Through the real `session_memory_*` handlers against the resolved
`AMSMemoryBackend` (status: `reachable`, transport `mcp`/`direct`):

- capture ok, id `a5bb8244-…`
- recall hit on attempt 1; stored representation
  `"T2-LIVE-CANARY-e5f1: contact [EMAIL] re parser deadlock"` — the
  PII-bearing canary redacted in AMS (CR-2)
- forget deleted 1; re-recall found nothing — cleanup confirmed

## 4 — Codex live MCP canary — UNPROBED (probed 2026-07-22, blocked pre-lift)

A LIVE Codex session ran the probe on 2026-07-22 (codex-cli 0.144.6,
`codex exec`, session id `019f8bbe-cf3d-7242-8f98-fcaad5ec1bc5`).
Codex honestly reported `session_memory_capture` / `_recall` /
`_forget` absent from its tool list and stopped without simulating
(D7 respected). Root cause is distribution, not transport: Codex
installs the attune-ai plugin from its git marketplace pinned to
origin/main (revision `34a78b53f` at run time), and the
`session_memory_*` adapters (`attune_redis/mcp_tools.py`) exist only
on the held T2 branch (#1594). The probe cannot pass until the held
stack #1593 → #1594 → #1596 → #1598 merges.

**2026-07-27 post-lift attempt (stack merged, 10.6.0 published):**
Codex marketplace re-synced (`codex plugin marketplace upgrade
attune-ai` → plugin 10.6.0). Headless probe (`codex exec`, session
`019fa35c-28b3-7130-afc7-786371096b52`) reached
`session_memory_capture` — the tool IS now in Codex's list (the
distribution blocker is gone) — but the call was auto-cancelled in
0.009s ("user cancelled MCP tool call"): codex's headless approval
policy denies MCP tool calls without `--full-auto`, and the
harness classifier (correctly) blocks spawning codex with
`--full-auto` from an agent session. Receipt stays UNPROBED; the
canary needs one INTERACTIVE Codex run of the same flow.

Post-lift procedure (07-27, after the stack merges): let the Codex
marketplace re-sync attune-ai, then run the canary flow —
`session_memory_capture` a dated canary → `session_memory_recall` →
`session_memory_forget` → re-recall empty — and append the transcript
here. (The 2026-07-22 diagnosis already verified generic
`redis_memory_*` round-trips from Codex; the `session_memory_*`
surface still needs its own receipt.)

## 5 — Claude Code hook canary (live, 2026-07-22)

Real `plugin/hooks/session_stash.py` invoked with a synthetic Stop
payload over stdin (nothing mocked — Ollama extraction live, real
backend resolution):

- hook exit 0; `stash.log`: `findings=1 written=1`; stash chip emitted
  via additionalContext
- semantic recall hit: stored text `"The root cause was
  T4-HOOK-CANARY-9d21, a double-free issue …"`, id `ce750c84-…`
- `forget_entries` deleted 1; re-recall empty — cleanup confirmed

The cross-SESSION leg is additionally evidenced organically: the
2026-07-22 T2 session's Stop hook stashed 5 findings whose stash-chip
ids were recalled verbatim by the next session's SessionStart hook.

## 6 — Antigravity/Gemini probe — UNPROBED (config recon 2026-07-22)

Read-only config recon, 2026-07-22: Antigravity DOES support MCP
servers — `~/.gemini/antigravity-ide/mcp_config.json` already
registers `attune-help` and `attune-author` via
`uvx --from <pkg>[plugin]`. The attune-ai plugin MCP server (the one
carrying `session_memory_*`) is NOT registered there, and a uvx
registration resolves PyPI `attune-ai` 10.5.0, which predates T2. So
the live probe sequences AFTER 10.6.0 publishes: register the server
in `mcp_config.json` (uvx-from-PyPI, matching the existing entries),
launch a live Antigravity session, confirm the tools appear, then run
the receipt-4 canary flow. If the tools never surface in a live
session, record an explicit `unsupported` row here. Automatic
lifecycle hooks are NOT promised on Codex or Antigravity (D2/R5).

## Canary cleanup register

- `T2-LIVE-CANARY-e5f1` — deleted 2026-07-22 (receipt 3)
- `T4-HOOK-CANARY-9d21` — deleted 2026-07-22 (receipt 5)
- `T5-CODEX-CANARY-6cf0` — never stored (receipt 4 probe: tools
  absent in Codex pre-lift; nothing to clean)
