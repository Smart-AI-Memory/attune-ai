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

## R6 — CLOSED (live Antigravity, 2026-07-28 09:47 EDT)

**PASS.** The cross-provider round trip is proven: packet created in
Claude Code on `claude/handoff-t4-docs`, resumed in a **different
vendor's** agent, which re-checked it against the real tree and
reported drift. Verbatim result:

```json
{
  "ok": true,
  "slug": "claude-handoff-t4-docs",
  "path": ".../attune-ai-github-issues-0aeac3/docs/handoffs/claude-handoff-t4-docs.md",
  "verified": {
    "base_ref": "origin/main",
    "branch": "claude/handoff-t4-docs",
    "changed_files": [],
    "created_at": "2026-07-28T03:01:42.717461+00:00",
    "head_sha": "3fed725b7396603f0aec41284593f4474b0a85f9",
    "merge_base": "3fed725b7396603f0aec41284593f4474b0a85f9",
    "provider": "claude-code"
  },
  "warnings": [
    {"code": "head_moved",
     "detail": "packet 3fed725b7 vs current afd3040f2"},
    {"code": "files_diverged",
     "detail": {"packet": [],
                "current": ["tests/unit/telemetry/test_memory_events.py"]}}
  ],
  "memory": {"status": "skipped", "reason": "not_implemented"}
}
```

`asserted.verification` still carries the caller's row as
`result: "not run"` — R1 honored end to end: the sending agent's
prose stayed quarantined from the git-rechecked `verified` facts.

**Receiving agent was Antigravity, not Codex** — a deliberate
substitution, recorded honestly. Codex auto-cancels MCP calls under
its headless `approval: never` policy (the same limit on transport
receipt 4), and the harness rightly blocks `--full-auto`. Antigravity
was already proven at 10.6.1 by transport receipt 6 and is equally a
different vendor, so it satisfies the cross-provider claim. The
packet's own prose still names Codex as the intended receiver; that
is the sending agent's claim, not a verified fact, and it is exactly
what the `asserted` block exists to hold.

**Command that worked** (run FROM the worktree — the MCP tool exposes
only `slug`; the repo root comes from the server's workspace):

```bash
cd <worktree> && agy --print 'Call the attune-ai MCP tool handoff_resume with slug "claude-handoff-t4-docs" and show the raw JSON result'
```

**Correction to the prior instruction — it was stale and would have
failed even after a successful approval.** It said run "with no
arguments", which was right on 07-27. That worktree has since moved to
`qa/memory-events`, and with no args the slug derives from the CURRENT
branch (`handoff/__init__.py`, `slugify_branch(snapshot()["branch"])`)
— so it would resolve `docs/handoffs/qa-memory-events.md`, miss, and
return `packet_not_found`, which reads like a broken feature rather
than a stale command. **Pass the slug explicitly whenever the worktree
may have moved.** The expected-drift note was also stale: `dirty_tree`
does NOT fire (the packet file is in `ignore_paths`); the real codes
are `head_moved` + `files_diverged`, which is a stronger receipt —
two of the three drift codes the launch article names.

Cosmetic, already chipped: `voice_summary` returned the generic
"Here's what I found." on this call too.
