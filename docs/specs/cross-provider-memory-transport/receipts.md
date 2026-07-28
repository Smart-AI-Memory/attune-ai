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
| 4 | Codex live MCP canary | PASS (live) | 2026-07-27 |
| 5 | Claude Code hook canary | PASS (live) | 2026-07-22 |
| 6 | Antigravity/Gemini probe | PASS (live, 10.6.1) | 2026-07-27 |

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

**2026-07-27 PASS (live, interactive Codex session ~08:01 ET,
plugin 10.6.0):** Patrick ran the four-leg canary interactively
(headless `codex exec` auto-cancels MCP approvals — see below). All
legs green with raw outputs: (1) capture `ok:true` id
`a1c7b6e0-2668-42c5-b14a-02e8770cbf36`; (2) recall returned the
stored representation `"R4-LIVE-CANARY-20260727: codex post-lift
probe, contact [EMAIL] re transport receipt"` — the CR-2 PII gate
redacted the canary email AT REST; (3) forget `requested:1
deleted:1`; (4) re-recall: canary token and id absent. Canary
deleted by the flow itself (D7 clean). Cosmetic finding chipped
separately: `voice_summary` is the generic "Here's what I found."
on capture/forget too.

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

**2026-07-27 PASS (live, attempt 2 vs PyPI 10.6.1):** with #1681's
stdout fix published in 10.6.1 and the uvx cache refreshed, the full
four-leg canary ran clean from a live `agy --print` session:
(1) capture `ok:true` id `671f8282-e5b3-4f96-ad86-c0db4c587390`;
(2) recall returned `"R6-LIVE-CANARY-20260727B: antigravity
post-10.6.1 probe, contact [EMAIL] re transport receipt"` — CR-2 PII
redaction at rest from the Antigravity seat; (3) forget; (4) final
recall verified the id absent. Distribution pre-check on the same
build: raw stdio harness against the uvx-served 10.6.1 server —
0 non-JSON stdout lines during a PII-logging capture. All receipts
in this ledger are now PASS — 6/6.

**2026-07-27 live probe (post-10.6.0 publish) — the receipt did its
job by FAILING on a real bug.** Steps executed: (1) uvx pre-warmed to
10.6.0; (2) raw stdio JSON-RPC handshake against the PyPI-served
server listed 60 tools incl. all 5 `session_memory_*` (distribution
receipt); (3) server registered in BOTH Antigravity configs
(`~/.gemini/antigravity-ide/mcp_config.json` for the IDE,
`~/.gemini/config/mcp_config.json` for the CLI — the CLI does NOT
read the IDE file; `.bak-r6` backups beside each) plus the scoped
permission grant `mcp(attune-ai/*)` in
`~/.gemini/config/config.json` `userSettings.globalPermissionGrants`
(grammar recovered from the agy binary: `mcp(server/*)`, NOT the
error message's `mcp(<target>)`; bare `mcp(attune-ai)` does not
match); (4) the live `agy --print` canary then failed leg 1 with
`calling "tools/call": invalid trailing data at the end of stream`.
Root cause reproduced with a raw harness: structlog is never
configured in the MCP server process, so its default STDOUT
PrintLogger interleaves the PII-gate's debug lines (`pii_scrubbed
pii_count=1 pii_types=['email']` — the gate itself works) with the
JSON-RPC frames; Antigravity's strict client rejects the stream while
Claude Code's lenient client masked the bug all along. Fix + red/green
regression test (spawn real server, assert stdout is JSON-only):
PR #1681. Receipt 6 can pass only against DISTRIBUTION, so it stays
blocked until the fix ships in a patch release (10.6.1 candidate) —
then re-run the canary flow above. Repro canary
`STDOUT-PURITY-CANARY`/id `0007863e-…` was stored server-side during
diagnosis and deleted the same hour (register below).

## Canary cleanup register

- `T2-LIVE-CANARY-e5f1` — deleted 2026-07-22 (receipt 3)
- `T4-HOOK-CANARY-9d21` — deleted 2026-07-22 (receipt 5)
- `R4-LIVE-CANARY-20260727` — deleted 2026-07-27 by the flow itself
  (receipt 4 PASS)
- `R6-REPRO-CANARY` / id `0007863e-6150-4326-a0ee-028154ca251d` —
  deleted 2026-07-27 (receipt 6 diagnosis; raw-harness forget,
  `deleted: 1`)
- `R6-LIVE-CANARY-20260727` — WAS stored server-side (the 10.6.0
  capture succeeded; only the response frame was corrupted — the
  earlier "never stored" note here was wrong); found via recall and
  deleted 2026-07-27
- `R6-LIVE-CANARY-20260727B` — deleted 2026-07-27 by the flow itself
  (receipt 6 PASS)
- `R6-DIST-VERIFY` — deleted 2026-07-27 (10.6.1 distribution
  pre-check; landed in the file stash, truncated)
- `STDOUT-PURITY-CANARY` ×4 — deleted 2026-07-27 (regression-test
  runs leaked to the live AMS store; test isolation fixed in #1685)
- `T5-CODEX-CANARY-6cf0` — never stored (receipt 4 probe: tools
  absent in Codex pre-lift; nothing to clean)
