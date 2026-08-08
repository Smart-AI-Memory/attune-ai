# Agent work handoff

## Goal

redis-config-truth rct-3: the doctor diagnostic — extend
`redis_health_check` to report the redacted effective config,
derived from the resolver's source-map, never from independent env
reads.

## Acceptance criteria

- `effective_config` section: source_map, redacted_url, overrides,
  classified health (R3) + detail.
- Incident shape names REDIS_URL as url source and REDIS_PASSWORD
  as present-and-merged.
- Rendered output contains no secret material.
- Health tool never breaks when attune core is absent.

## Scope and assumptions

- Branch/worktree: `claude/rct-3-doctor-diagnostic` off origin/main
  (post-#1985).
- Provider/session: Claude lead, 2026-08-08 starter session.
- Assumptions: `attune_redis.mcp_tools.handle_redis_health_check`
  is the single implementation surface; tool input_schema stays
  frozen (D6) — payload extension is additive.

## Current state

- Status: implemented + tested; PR open, D11 lane pending/run (see
  PR comments); tasks.md flip waits for #1986 to merge (same
  paragraph — guaranteed conflict otherwise).
- Changed files: `attune_redis/mcp_tools.py`
  (`_effective_config_report` + handler extension),
  `tests/unit/memory/test_redis_doctor_diagnostic.py` (9 tests).
- Decisions: classifier supplies health + scrubbed detail; on
  malformed config the report carries health/detail without a
  source_map (resolver raised); `backend_selected` = backend class
  name in the handler payload.
- Risks or open questions: none open.

## Verification

| Claim | Failure-sensitive probe | Result |
| --- | --- | --- |
| Incident shape sources named | `test_incident_shape_names_sources_and_merges_password` | pass |
| No secret in rendered output | `test_rendered_output_contains_no_secret_material` + live-fire grep | pass |
| Core-absent degrade | `test_attune_core_absent_degrades_gracefully` | pass |
| Live-fire | real requirepass env: healthy, sources named, leak-grep False | pass |
| Ratchet sweep | tests/unit/gates/ + tests/unit/quality/ serial | 210 passed |

## Next action

After #1986 merges: rebase, flip tasks.md (rct-3 in review) on this
branch. Chair merge read on explicit go; delete this file when the
branch merges. Next rung: rct-4 (consumer migration + drift guard).
