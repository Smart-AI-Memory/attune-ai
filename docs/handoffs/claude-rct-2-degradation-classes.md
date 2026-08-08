# Agent work handoff

## Goal

redis-config-truth rct-2: classified loud-once degradation at the
resolver-consumer seam — health states (healthy / degraded_auth /
degraded_connectivity / disabled), auth and malformed-config warn
ONCE per session, server-absent stays silent, P15 never-block holds.

## Acceptance criteria

- `MemoryFeatures.classify_redis_health()` returns a typed
  `RedisHealthReport` for every failure class, never raises.
- AuthenticationError produces exactly ONE visible notice per
  session (first and second call both tested).
- ConnectionRefused produces no notice (silent degrade).
- No workflow blocks in any failure class.
- Secrets redacted in every message.

## Scope and assumptions

- Branch/worktree: `claude/rct-2-degradation-classes` (built atop
  `claude/rct-1-canonical-resolver`; rebase onto origin/main once
  PR #1984's squash lands, then open its own PR).
- Provider/session: Claude lead, 2026-08-08 starter session.
- Assumptions: resolver (`resolve_redis_connection`) is the only
  connection source for the seam; `ATTUNE_REDIS_MOCK=true` is the
  intentional-disable signal.

## Current state

- Status: implemented + tested; awaiting #1984 merge to rebase and
  open the rct-2 PR.
- Changed files: `src/attune/memory/features.py` (states, report,
  classifier, loud-once, check_redis rewire),
  `src/attune/memory/__init__.py` (exports),
  `tests/unit/memory/test_redis_degradation_classes.py` (12 tests).
- Decisions: malformed config joins `degraded_auth` (never
  self-heals, per R3); missing redis package maps to
  `degraded_connectivity` (silent, matches today's quiet fallback);
  loud-once scope is per-process, reopened only by
  `reset_redis_health_warnings()`.
- Risks or open questions: none open; notice-spam risk pinned by
  `test_reset_reopens_the_once_scope`.

## Verification

| Claim | Failure-sensitive probe | Result |
| --- | --- | --- |
| Auth warns exactly once | `test_auth_failure_warns_exactly_once` (serial) | pass |
| Refused stays silent | `test_connection_refused_stays_silent` | pass |
| Never blocks | `TestNeverBlock` (5 exception classes + malformed config) | pass |
| Redaction | `test_warning_message_redacts_password` + live-fire | pass |
| Live-fire | real requirepass Redis: right pw → healthy; wrong pw → one redacted notice, False twice | pass |
| Regression | features/fallback/no-server suites 60 passed serially | pass |

## Next action

After PR #1984 merges: `git rebase --onto origin/main
claude/rct-1-canonical-resolver claude/rct-2-degradation-classes`,
re-sign, push, open the rct-2 PR off main, flip tasks.md status.
