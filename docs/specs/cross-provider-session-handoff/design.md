# Cross-Provider Session Handoff — Design

**Status:** approved (2026-07-22) — design D1–D6 ratified by the
chair as drafted.
**Slug:** `cross-provider-session-handoff`

## Shape

Core logic in a new `src/attune/handoff/` module; MCP surface
registered on the main attune server per the plugin-reference
checklist (schema in `tool_schemas.py`, handler, dispatch entry,
tool-count test, skill reference). No redis-package coupling — the
memory linkage goes through the same internal helpers the
`session_memory_*` handlers use, and degrades silently (R3).

```text
src/attune/handoff/
├── __init__.py      # handoff_create(), handoff_resume() public API
├── packet.py        # assemble/render/parse the packet file
└── verify.py        # drift matrix vs current git state
```

## D1 — packet file: markdown body + YAML frontmatter

`docs/handoffs/<branch-slug>.md` stays the contract's location and
template, with one addition: machine-readable YAML frontmatter
carrying the VERIFIED fields (`branch`, `head_sha`, `merge_base`,
`changed_files`, `created_at`, `provider`). The markdown body holds
the ASSERTED prose (goal, acceptance criteria, decisions, risks,
next action). `handoff_resume` re-checks frontmatter fields against
git; body fields are surfaced as-is under an `asserted:` key. This
keeps the file human-readable (the contract's existing consumers
lose nothing) while making verification mechanical.

## D2 — git reads via subprocess, read-only, path-validated

`verify.py` shells to git (`branch --show-current`, `merge-base`,
`diff --name-only`, `rev-parse`) with validated paths and no
mutating commands anywhere in the module. Resume therefore works in
read-restricted sandboxes (R4); create needs workspace write only
for the packet file itself.

## D3 — drift matrix (R2 warning codes)

| Code | Trigger |
|------|---------|
| `branch_missing` | packet branch absent from the repo |
| `head_moved` | current HEAD != packet `head_sha` |
| `files_diverged` | actual diff set != packet `changed_files` |
| `packet_stale_days` | `created_at` older than N days (report-only) |
| `dirty_tree` | uncommitted changes present at resume time |

All warnings are additive report fields — never blocking, never
auto-fixed. The report's top-level key order is `verified`,
`warnings`, `asserted`, `memory` (verified-first mirrors the
contract's authority model).

## D4 — caps (R5, concrete numbers)

- Body cap: 8 KB total rendered packet; per-field cap 2 KB.
- Oversize input → `{ok: false, reason: field_over_cap, field,
  limit}`; never silent truncation.
- Re-create on an existing slug overwrites in place (one packet per
  branch); the previous packet's `created_at` is preserved in a
  `superseded_at` frontmatter field for staleness honesty.

## D5 — memory linkage internals

`handoff_create` calls the session-stash capture helper directly
(same code path the `session_memory_capture` handler wraps) with
topic `handoff`; `handoff_resume` runs a recall for the slug.
Backend resolution failures are caught per the contract's
degrade-silently rule and reported as `memory: skipped` with the
reason string — the same truthful-status discipline as the
transport spec's R2.

## D6 — telemetry

Both tools emit one structlog event each (`handoff_create`,
`handoff_resume`) with slug, warning codes, duration, and the
memory-linkage outcome — same shape as the T4' transport fields, so
provider-boundary usage becomes readable at the 07-27-style usage
reads.

## Explicitly not designed here

- CLI wrapper (`attune handoff …`) — deferred until MCP usage
  signal exists; MCP-only at ship.
- Any auto-invocation (hooks) — non-goal per requirements.
- Cross-repo handoffs — packet is branch-scoped within one repo.

## Test plan (maps to R6)

- `tests/unit/handoff/test_packet.py` — assemble from a fixture
  repo; frontmatter fields provably git-derived; cap rejections.
- `tests/unit/handoff/test_verify.py` — the D3 matrix, one case
  per code, plus the clean path.
- `tests/integration/test_mcp_dispatch.py` — extend the transport
  spec's real-dispatch class with the two new tools.
- Live receipt post-lift (receipts.md ledger, UNPROBED until run).
