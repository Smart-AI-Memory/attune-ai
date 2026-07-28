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

## 2026-07-27 — T4 docs projected + R6 probe (Claude leg PASS, Codex leg reached-not-executed)

- **Feature page** — `content/features/session-handoff.md` authored
  per the single-source playbook; projected to 10 `.help` kinds + 4
  docs pages; bundle synced. Gates: `audit_doc_imports` clean,
  `audit_docs_wiring` no findings, `tests/unit/help` 410 passed
  (serial).
- **Claude leg (live, real MCP tool)** — `handoff_create` called
  through this session's attune MCP server (plugin 10.6.1) on branch
  `claude/handoff-t4-docs`: `ok:true`, packet written to
  `docs/handoffs/claude-handoff-t4-docs.md`, git-derived
  `head_sha 3fed725b7…`, verification row stored with
  `result: "not run"` (R1 honored). `memory: {skipped,
  not_implemented}` — honest: the published 10.6.1 server predates
  the T3 linkage merged to main the same evening (#1694); the wired
  status ships with the next release.
- **Codex leg (live, headless)** — codex-cli 0.144.6, session id
  `019fa6ac-0db1-7a83-a48f-753912ea88f2`, workdir = the branch's
  worktree. `handoff_resume` IS in Codex's tool list and dispatch
  started (`mcp: attune-ai/handoff_resume started`) — the
  distribution claim is PROVEN at 10.6.1 — but the call was
  auto-cancelled by codex's headless approval policy
  (`approval: never` → "user cancelled MCP tool call"), the same
  limit recorded on the transport spec's receipt 4. Verbatim raw
  result: `[{"type":"text","text":"user cancelled MCP tool call"}]`.

## R6 — one interactive Codex run still owed (UNPROBED past dispatch)

The packet sits uncommitted at
`docs/handoffs/claude-handoff-t4-docs.md` in the
`attune-ai-github-issues-0aeac3` worktree. To close R6, run ONE
interactive Codex session from that worktree and approve the call:

```bash
codex "Call the attune-ai MCP tool handoff_resume with no arguments and show the raw JSON result"
```

Expected: `ok:true`, `verified.branch = claude/handoff-t4-docs`,
drift warnings listing the uncommitted tree (`dirty_tree`) — append
the transcript here.
