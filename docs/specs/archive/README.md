# Archived Specs

Specs that are complete, obsolete, or superseded. Moved here so
the active `docs/specs/` directory reflects only in-flight work.

The session-start hook (`plugin/hooks/spec_orient.py`) walks
`docs/specs/` one level deep — `archive/` itself has no spec
files at its top level, so the discovered "spec dir" returns
`None` from `_phase_for_dir` and is silently skipped. Archived
specs do NOT appear in session orientation.

## Archived 2026-05-12

| Spec | Why archived |
|---|---|
| `telemetry/` | Complete since v3.8.2; ongoing maintenance lives in code. |
| `ci-debt/` | Complete 2026-05-10 across Phases A/B/C. |
| `probe-c-memory-investigation/` | Resolved same-day with one-line `patch("threading.Thread")` fix. Lesson preserved in CLAUDE.md. |
| `ops-specs-features/` | Shipped in three phases (PR #236 / #239 / #240). |
| `ops-security-hardening/` | Implemented in PR #254 (`a5c50bd1`). |
| `larger-runners/` | Closed — Probe-C resolved the OOM concern; spec itself admits the case is smaller now. |

## Why archive instead of delete

Git history preserves the analysis, but archive makes the
reasoning easier to find without `git log` archaeology. Useful
when a similar problem surfaces months later and you want to
check whether you considered it before.

## When to revisit

- An archived spec is relevant again? Move it back to
  `docs/specs/` (with a note in `decisions.md` explaining the
  unarchive).
- An archived spec was wrong (the resolution didn't hold)? Open
  a new spec that supersedes it; cross-link.
