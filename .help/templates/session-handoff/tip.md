---
type: tip
name: session-handoff-tip
feature: session-handoff
depth: tip
generated_at: 2026-07-28T03:00:44.232722+00:00
source_hash: 963aaf0dd059e464542f852a8b8c1f93be3beb0bbf89675536ba711fe6d47c66
status: generated
---

# Cross-provider session handoff — verified packet create/resume so any agent can pick up a branch mid-flight

## Notes & tips

- Delete the packet when its branch merges — the file is branch-scoped
  working state, not documentation.
- Fill `verification` rows with the probes you actually intend the
  receiver to run; the "not run" default keeps everyone honest.
- Both tools emit one structlog event each (`handoff_create`,
  `handoff_resume`) with the slug, warning codes, duration, and the
  memory outcome — provider-boundary usage shows up in telemetry
  reads.
