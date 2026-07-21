# Rescue: Visual Debate Theater UI components

Rescued from Antigravity's PR-4 track (round-table thread
`q-review-five-implementation-plans-001`), which was written to the
non-repo `~/antigravity IDE/` directory.

These React components (`DebateGraph.tsx`, `ExecutiveChairPanel.tsx`)
are **parked here, not served or built by this repo** — attune-ai has
no `attune-gui/` tree; the GUI is a separate project. Disposition:

- Move to the attune-gui project when the debate-theater surface is
  picked up, wiring against `attune.roundtable.stream` events.
- Note the gap between the plan and this code: no WebSocket client, no
  Cytoscape graph (it renders a card grid), no event wiring — these
  are static prop-driven components.

Delete this directory when relocation happens (or when the track is
ruled dead).
