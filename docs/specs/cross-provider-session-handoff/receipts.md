# Cross-Provider Session Handoff — Receipts

Evidence ledger (R6 discipline): rows record probes actually run,
dated, with results verbatim. UNPROBED rows stay honest until the
named client runs.

## 2026-07-27 — T3 memory linkage: suite + live local canary

- **Suite receipt** — `tests/unit/handoff/` +
  `tests/integration/test_mcp_dispatch_handoff.py` run SERIALLY
  (`-p no:xdist`): `35 passed`. Includes the unreachable-backend
  path asserting `memory == {status: skipped, reason: no_backend}`
  with `ok` staying true, and the real-dispatch linkage test
  (capture through the real sanitizer, recall through the real
  dispatch chain).
- **Live local canary (Claude side)** — temp fixture repo,
  real backend resolution (`AMSMemoryBackend`, local Redis AMS):
  `handoff_create` → `memory.status=captured`
  (id `6ddf8227-cb74-4fc3-8a44-0c69ace07483`), `handoff_resume` →
  `memory.status=recalled` with the pointer id among results;
  canary then forgotten via `forget_entries` (deleted=1). Structlog
  events observed with the real memory outcome:
  `handoff_create … memory=captured`,
  `handoff_resume … memory=recalled` (D6).

## R6 live cross-provider receipt — UNPROBED

- **Claude Code → Codex resume** — UNPROBED. Packet created in
  Claude Code, resumed in a live Codex session (post-distribution;
  10.6.1 is on PyPI and the marketplaces, so this row is runnable).
  T4 owns filling it with the session id + verbatim tool results.
