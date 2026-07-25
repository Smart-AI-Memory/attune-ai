---
type: troubleshooting
name: elicitation-forms-troubleshooting
feature: elicitation-forms
depth: troubleshooting
generated_at: 2026-07-25T05:20:20.482906+00:00
source_hash: 660990a441ecd2b722e6ade0d914a0d81e15357900f19a08cc3f511a5b9b13ff
status: generated
---

# Dynamic forms and the agent-to-user communication grammar

## Failure modes

### Rendering on a surface that has none

If a form is rendered to the widget surface but the client cannot post
back (`sendPrompt` unavailable), the submit button reports it and the
caller should fall back to `form_to_askuserquestion`. A rich widget needs
a widget-capable client; a plain terminal degrades to the menu fallback
by design.

### "Registered ≠ working until the server reboots"

A newly added construct or field reaches the live MCP server only after
the server restarts on the new version — the tool schema is loaded at
startup. Verify the live `elicitation_render_widget` schema actually
carries a new enum value before asserting the construct works end-to-end.

### A `progress` form whose blocked items disagree with its options

The bridge enforces `set(blocked labels) == set(options)`; a mismatch
raises `FormValidationError`. The picker can never offer a non-existent
blocker or omit a real one.
