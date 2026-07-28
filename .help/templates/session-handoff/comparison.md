---
type: comparison
name: session-handoff-comparison
feature: session-handoff
depth: comparison
generated_at: 2026-07-28T03:00:44.232722+00:00
source_hash: 963aaf0dd059e464542f852a8b8c1f93be3beb0bbf89675536ba711fe6d47c66
status: generated
---

# Cross-provider session handoff — verified packet create/resume so any agent can pick up a branch mid-flight

## Comparison

- **vs. the handoff *contract* file alone** — the collaboration
  contract already tracks `docs/handoffs/<branch-slug>.md` as a
  hand-written file. Session-handoff keeps that location and template
  but makes the facts machine-derived and re-checkable: a receiving
  agent no longer has to trust that the listed SHA or file set is
  current.
- **vs. session memory (`session_memory_*`)** — the stash carries
  small cross-session findings; a handoff packet carries one branch's
  full working state. They link: create stashes a pointer so recall
  surfaces the handoff, but the packet file is the artifact.
- **vs. `/spec` documents** — a spec captures multi-session design
  intent; a packet captures a moment: this branch, this HEAD, this
  next action.
