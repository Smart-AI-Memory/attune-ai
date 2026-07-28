---
name: session-handoff
source: content/features/session-handoff.md
tags:
- handoff
- collaboration
- multi-llm
- memory
type: tip
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
