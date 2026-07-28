# Cross-Provider Memory Transport — Tasks

**Status:** shipped (2026-07-28) — the held stack lifted as planned on
2026-07-27: T1 #1593, T2 #1594, T3 #1596, T5 #1598 all MERGED, each
re-targeted to main before its base branch was deleted. All six R8
boundary receipts PASS (4 live) — see `receipts.md`. Execution evidence
and the live AMS receipt remain in `decisions.md` (D3 execution
evidence section).

Remaining work was re-measured against the built state on 2026-07-22 and
consolidated: most of T4-as-written was already satisfied by T1–T3 (hooks
needed no adaptation — status fields are additive and both hooks already
consume `backend_status()`; the skill matrix landed in T3). What is left:

- **T4′ (buildable now):** telemetry transport/failure fields + author
  `receipts.md` + formalize the Claude hook canary — see below.
- **T5′ (deferred tail):** Codex and Antigravity/Gemini live probes —
  each requires that client to be running; they cannot be executed
  from a Claude Code session and land whenever those clients next run
  (naturally after 2026-07-27).

The original T4/T5 XML blocks are preserved below the built tasks for
provenance, superseded by T4′/T5′.

## T1 — Truthful fallback and status contract — BUILT (held #1593)

```xml
<task id="T1" name="truthful-fallback-status">
  <objective>Make failed file writes return false and add caller-scoped reachability fields without breaking existing status keys.</objective>
  <files-to-modify>
    <file path="src/attune/memory/file_stash.py">Return the durable replace result from _rewrite and remember.</file>
    <file path="src/attune/memory/session_stash.py">Add compatible reachability/reason fields and preserve never-raises behavior.</file>
    <file path="tests/unit/memory/test_file_stash.py">Add EPERM false-success regression.</file>
    <file path="tests/unit/memory/test_session_stash.py">Cover additive status fields and local denial.</file>
    <file path="CHANGELOG.md">Document the public false-success correction.</file>
  </files-to-modify>
  <validation>
    <check>pytest tests/unit/memory/test_file_stash.py tests/unit/memory/test_session_stash.py -q</check>
    <check>EPERM through public stash_entry() returns false and exposes a visible reason.</check>
    <check>Search all status consumers for exact-dict assumptions and run the complete status-consuming suite.</check>
  </validation>
  <risks><risk severity="medium">Audit callers that assumed unconditional true.</risk></risks>
</task>
```

## T2 — Semantics gap and provider-neutral MCP handlers — BUILT (held #1594)

Built 2026-07-22. Also fixed a bug the CR-2 canary caught: the
session-stash PII/secrets gate was a constructor-defaults no-op; both
scrubbers are now explicitly enabled (PII redacts, secrets fail closed).
Live AMS capture → recall → forget receipt (R8 #3) recorded in
`decisions.md`.

```xml
<task id="T2" name="session-memory-mcp" depends-on="T1">
  <objective>Add thin session_memory adapters for the proven sanitization, cwd, and TTL gap while preserving generic redis_memory tools.</objective>
  <files-to-modify>
    <file path="attune_redis/mcp_tools.py">Conditionally add capture/recall/recent/forget/status handlers delegating to session_stash.</file>
    <file path="attune_redis/tests/test_mcp_tools.py">Freeze old schemas and test any additive tools.</file>
    <file path="tests/integration/test_mcp_dispatch.py">Exercise the real registration and dispatch chain.</file>
    <file path="docs/specs/cross-provider-memory-transport/decisions.md">Record the D3 semantics-gap verdict.</file>
  </files-to-modify>
  <validation>
    <check>Real MCP dispatch succeeds; direct handler-only mocks are insufficient.</check>
    <check>Disposable AMS capture → search → forget succeeds and cleanup is confirmed.</check>
    <check>A PII-bearing live canary is sanitized in the stored representation.</check>
    <check>Python false maps to MCP {ok:false, reason:&lt;stable_code&gt;}.</check>
    <check>Existing redis_memory_* schemas remain unchanged.</check>
  </validation>
  <risks><risk severity="medium">Do not duplicate a Redis tool that already preserves the contract.</risk></risks>
</task>
```

## T3 — Provider routing in the recall skill — BUILT (held #1596)

Built 2026-07-22. Also extended the plugin reference validator to
include attune_redis-registered tool names, so the skill's MCP Tools
table is CI-validated.

```xml
<task id="T3" name="recall-skill-routing" depends-on="T2">
  <objective>Route trusted hooks to Python, MCP-capable clients to MCP, and all others to an honest degraded result.</objective>
  <files-to-modify>
    <file path="plugin/skills/recall/SKILL.md">Replace the universal Python recipe with capability routing and truthful status language.</file>
    <file path=".agents/skills/recall/SKILL.md">Generated mirror; never edit directly.</file>
  </files-to-modify>
  <validation>
    <check>python scripts/sync_agents_skills.py --write</check>
    <check>Projection drift guard passes.</check>
    <check>MCP clients are never instructed to run sandboxed Python for memory.</check>
    <check>Finding capture names session_memory_capture and never redis_memory_store.</check>
  </validation>
  <risks><risk severity="high">Edit the plugin source first; committing only the mirror violates the single-source rule.</risk></risks>
</task>
```

## T4′ — Telemetry fields, receipts, hook canary (consolidated remainder)

```xml
<task id="T4p" name="telemetry-receipts-canary" depends-on="T3">
  <objective>Make degraded routing observable in local telemetry and record the receipts ledger; formalize the Claude hook canary.</objective>
  <files-to-modify>
    <file path="plugin/hooks/session_stash.py">Add backend/transport/reason fields (from backend_status) to the session_stash event emission.</file>
    <file path="plugin/hooks/session_recall.py">Same additive fields on the session_recall emissions.</file>
    <file path="tests/unit/hooks">Cover the new event fields.</file>
  </files-to-modify>
  <files-to-create>
    <file path="docs/specs/cross-provider-memory-transport/receipts.md">Dated R8 ledger: receipts 1-3 (done, from decisions.md), 5 (hook canary), honest unprobed rows for 4 and 6.</file>
  </files-to-create>
  <validation>
    <check>Focused hook suites pass; telemetry stays local-only and default-off.</check>
    <check>Claude hook canary: capture via the real hook path, recall, forget, cleanup confirmed.</check>
    <check>Documentation promises no automatic hooks on Codex or Antigravity.</check>
  </validation>
</task>
```

## T5′ — Deferred provider probes (tail)

Codex MCP canary (R8 #4) and Antigravity/Gemini probe-or-unsupported
(R8 #6). Each requires a live session of that client; append results
to `receipts.md` from the next Codex / Antigravity session. A
synthetic or mocked provider pass remains forbidden.

## Superseded original T4 (provenance)

```xml
<task id="T4" name="hooks-docs-telemetry" depends-on="T3">
  <objective>Re-verify Claude lifecycle hooks, document capability tiers, and make degraded routing observable.</objective>
  <files-to-modify>
    <file path="plugin/hooks/session_stash.py">Adapt only if additive status fields require it.</file>
    <file path="plugin/hooks/session_recall.py">Preserve host-side behavior and legible degradation.</file>
    <file path="plugin/skills/recall/SKILL.md">Document the final matrix and operation receipts.</file>
    <file path="src/attune/telemetry/memory_events.py">Add local-only transport/backend and failure-reason signals if absent.</file>
  </files-to-modify>
  <validation>
    <check>Focused hook and telemetry unit suites pass.</check>
    <check>Claude Code hook canary is captured, recalled next session, and deleted.</check>
    <check>Telemetry remains local-only and default-off.</check>
  </validation>
  <risks><risk severity="medium">Documentation must not promise automatic hooks on Codex or Antigravity.</risk></risks>
</task>
```

## Superseded original T5 (provenance)

```xml
<task id="T5" name="provider-live-matrix" depends-on="T4">
  <objective>Prove the shipped boundary across providers and record honest unsupported states.</objective>
  <files-to-create>
    <file path="docs/specs/cross-provider-memory-transport/receipts.md">Dated commands/results and cleanup confirmation for every R8 receipt.</file>
  </files-to-create>
  <validation>
    <check>Codex MCP capture → recall → forget passes.</check>
    <check>Claude hook capture → next-session recall → forget passes.</check>
    <check>Antigravity/Gemini records MCP success or an explicit unsupported/unprobed result.</check>
    <check>Search confirms zero diagnostic canaries remain.</check>
  </validation>
  <risks><risk severity="high">A synthetic or mocked provider pass is forbidden.</risk></risks>
</task>
```
