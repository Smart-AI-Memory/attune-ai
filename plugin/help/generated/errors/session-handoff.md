---
name: session-handoff
source: content/features/session-handoff.md
tags:
- handoff
- collaboration
- multi-llm
- memory
type: error
---

# Cross-provider session handoff — verified packet create/resume so any agent can pick up a branch mid-flight

## Failure modes

- **Resume warns `head_moved` / `files_diverged` on your own
  branch** — someone (possibly you, in another session) committed
  after the packet was created. Read the diff before trusting the
  packet's `current_state`; re-create the packet after material
  changes.
- **`memory: skipped` with `no_backend`** — the memory tier is
  unreachable from this process. The packet itself is unaffected;
  recall-based discovery of the handoff just will not fire.
- **Cap rejections on create** — the packet is a pointer, not a
  design doc. Move long prose into the spec or the branch's docs and
  reference it from the packet.
- **A stale packet (`packet_stale_days`)** — packets outlive their
  usefulness fast; treat one older than a week as archaeology, not
  instruction.
