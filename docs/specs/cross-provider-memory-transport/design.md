# Cross-Provider Memory Transport — Design

**Status:** APPROVED — implementation authorized 2026-07-22.

## Transport flows

### MCP-capable client

Codex and any MCP-capable provider call Attune tools. The MCP server runs
host-side with real network and filesystem access and delegates to
`session_stash`, so sanitization, TTL, and cwd semantics stay centralized.

```text
agent → session_memory_capture (MCP host) → session_stash.stash_entry → AMS
agent → session_memory_recall  (MCP host) → session_stash.recall_entries
```

Nothing memory-critical executes inside the agent sandbox.

### Lifecycle-hook client

Claude Code continues to run `plugin/hooks/session_stash.py` and
`plugin/hooks/session_recall.py` in a trusted host context. Those hooks call
`session_stash` directly. MCP remains available for on-demand operations.

### Client with neither capability

The integration reports capability status first. If the file backend is
writable, the client may use explicitly degraded local-file mode. If it is
not writable, the operation returns `unsupported` with a reason. It never
reports success and never converts a caller-local failure into "Redis is
down."

## Proposed provider-neutral MCP surface

The verified `redis_memory_*` surface remains a generic working-memory API;
it does not implement the full `session_stash` sanitization, cwd, and TTL
contract. Finding capture therefore uses these additive tools in
`attune_redis/mcp_tools.py`:

- `session_memory_capture(kind, content, cwd?, session_id?, tags?)`
- `session_memory_recall(query, limit<=10, cwd?)`
- `session_memory_recent(limit<=20, cwd?)`
- `session_memory_forget(ids)`
- `session_memory_status()`

Each handler is a thin adapter over `src/attune/memory/session_stash.py`.
Existing `redis_memory_*` tools remain untouched. No tool duplicates an
existing operation that already preserves the required semantics.

Python write results map explicitly onto MCP results: `True` becomes
`{"ok": true, "reason": null}`; `False` becomes
`{"ok": false, "reason": "<stable_reason_code>"}`. The adapter never
turns a false Python result into MCP success. `session_memory_recent`
delegates to the existing backend rather than reimplementing ordering.

## Status and operation results

Existing status fields stay compatible. New fields are additive:

```json
{
  "backend": "AMSMemoryBackend",
  "fallback": false,
  "unreachable_upgrade": null,
  "ok": true,
  "transport": "mcp|direct|file|none",
  "reachability": "reachable|unreachable_local|unknown",
  "reason": null
}
```

Write operations return `ok=false` after any non-durable write. A reason such
as `file_write_denied`, `network_blocked_local`, or `bridge_unavailable`
describes the caller's observed boundary without asserting global service
health.

Example from a sandbox that cannot reach localhost or write the fallback:

```json
{
  "backend": "FileStashBackend",
  "fallback": true,
  "ok": false,
  "transport": "none",
  "reachability": "unreachable_local",
  "reason": "file_write_denied"
}
```

## Routing algorithm

1. Trusted host hook or CLI: call Python `session_stash` directly.
2. Otherwise, when Attune MCP tools are available: use MCP exclusively.
3. Otherwise, test file-backend writability with a real temporary write and
   remove the probe artifact on every success and failure path.
4. Writable file backend: use explicit degraded mode and label it.
5. Unwritable file backend: return `unsupported` with the observed reason.
6. Never infer global Redis health from steps 3–5.

`plugin/skills/recall/SKILL.md` owns the portable routing instructions.
`.agents/skills/recall/SKILL.md` is generated with
`python scripts/sync_agents_skills.py --write` and is never edited directly.

## Security

- MCP handlers use narrow validated schemas, bounded content/result sizes,
  and validated cwd/path inputs.
- PII and secret sanitization runs inside `session_stash` for every capture.
- Credentials never appear in status or operation responses.
- The adapter exposes no arbitrary file access or network proxy.
- Sandbox policy remains unchanged; host-side MCP crosses the boundary by
  the client's intended tool mechanism.

## Compatibility and migration

- Freeze `redis_memory_*` schemas with tests.
- Treat the `FileStashBackend.remember()` return correction as a bug fix.
- Record the public true-to-false behavior correction in `CHANGELOG.md`.
- Audit callers that ignore write results and make failures legible at their
  natural attention surface.
- Change the recall skill source and regenerate its `.agents` mirror in the
  same PR.

## Telemetry

Record local-only counts for selected transport/backend, failed-write reason,
and `unreachable_local`. Preserve the existing default-off posture. These
signals reveal whether clients repeatedly land in degraded tiers without
storing content or credentials.

## Verification

- Unit: `EPERM` regression; additive status shape; routing order.
- Integration: real MCP dispatch; disposable AMS capture/search/forget.
- Live matrix: Codex MCP canary, Claude hook canary, Antigravity/Gemini
  capability probe. Record unsupported honestly. Delete all canaries.

## Rollback

Tasks land independently. Skill rollback reverts the source and regenerates
the mirror. Additive MCP handlers can be removed without changing existing
Redis tools. The false-success fix must not be rolled back; any caller that
depended on unconditional `True` must be corrected instead.
