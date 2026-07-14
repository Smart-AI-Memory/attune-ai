---
type: warning
name: elicitation-forms-warning
feature: elicitation-forms
depth: warning
generated_at: 2026-07-14T15:58:51.698621+00:00
source_hash: ea2a2694719d75bff1894657cfe5e0f5c96ae71719ae4d7f00ce7252b9e9798a
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
